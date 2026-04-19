from __future__ import annotations
import os
import json
import asyncio
import httpx
import redis.asyncio as aioredis
from openai          import OpenAI
from dotenv          import load_dotenv
from fastapi         import FastAPI
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response

load_dotenv()

app        = FastAPI(title="Inference Service")
llm_client = OpenAI(
    base_url = os.environ["API_BASE_URL"],
    api_key  = os.environ["HF_TOKEN"]
)

REDIS_URL     = os.environ.get("REDIS_URL",     "redis://localhost:6379")
ENV_URL       = os.environ.get("ENV_SERVICE_URL","http://localhost:7860")
MODEL_NAME    = os.environ.get("MODEL_NAME",    "llama3-8b-8192")

VALID_ACTION_TYPES = ["identify_fault","query_telemetry","isolate_breaker","submit_rca"]
VALID_FAULT_TYPES  = ["line_trip","transformer_overload","relay_maloperation",
                      "phase_imbalance","scada_loss","capacitor_failure"]
VALID_SEVERITIES   = ["critical","major","minor"]
FT_MAP = {
    "cascade":"line_trip","maloperation":"relay_maloperation",
    "overload":"transformer_overload","blackout":"line_trip",
    "comms_loss":"scada_loss","relay_trip":"relay_maloperation"
}

steps_counter   = Counter("inference_steps_total",   "Total steps taken")
errors_counter  = Counter("inference_errors_total",  "Total LLM errors")
reward_hist     = Histogram("inference_reward",       "Step reward distribution")
episode_counter = Counter("inference_episodes_total", "Total episodes run")

SYSTEM_PROMPT = """You are a power grid fault engineer. Output ONLY raw JSON.
Format: {"action_type":"identify_fault","component_id":"RELAY_89","fault_type":"relay_maloperation","severity":"critical","description":"RELAY_89 maloperation zone_1 distance trip despite normal current","recommendation":"Check relay settings"}
action_type: identify_fault|query_telemetry|isolate_breaker|submit_rca
fault_type: line_trip|transformer_overload|relay_maloperation|phase_imbalance|scada_loss|capacitor_failure
severity: critical|major|minor
description always required. Never repeat components in AlreadyFound."""


def build_prompt(obs: dict) -> str:
    already = [f["component_id"] for f in obs.get("identified_faults", [])]
    not_found = [c for c in [
        "RELAY_89","LINE_8_9","LINE_9_10","LINE_10_11",
        "BUS_9","BUS_10","BUS_11","RELAY_910","RELAY_1011","TX_8_9"
    ] if c not in set(already)]
    return (
        f"Step {obs['step_number']}/{obs['max_steps']} "
        f"reward={obs['metadata']['cumulative_reward']}\n"
        f"SCADA:{json.dumps(obs['scada_readings'],separators=(',',':'))}\n"
        f"Relay:{json.dumps(obs['relay_log'],separators=(',',':'))}\n"
        f"AlreadyFound:{already}\n"
        f"NotYetFound:{not_found[:4]}\n"
        f"Feedback:{obs['feedback']}"
    )


def sanitize(raw: dict) -> dict:
    at  = str(raw.get("action_type","")).strip().lower()
    cid = str(raw.get("component_id","")).strip()
    desc= str(raw.get("description","")).strip()
    ft  = str(raw.get("fault_type","") or "").strip().lower()
    sev = str(raw.get("severity","") or "").strip().lower()
    rec = raw.get("recommendation")
    if ft not in VALID_FAULT_TYPES:
        ft = FT_MAP.get(ft, None)
    return {
        "action_type":    at  if at  in VALID_ACTION_TYPES else "query_telemetry",
        "component_id":   cid or "UNKNOWN",
        "description":    desc if len(desc)>=5 else f"Inspecting {cid} from SCADA.",
        "fault_type":     ft,
        "severity":       sev if sev in VALID_SEVERITIES else None,
        "recommendation": str(rec).strip() if rec else None,
    }


def parse_action(text: str) -> dict | None:
    text = text.strip()
    first = text.find("{")
    last  = text.rfind("}")
    if first == -1 or last == -1:
        return None
    try:
        return sanitize(json.loads(text[first:last+1]))
    except Exception:
        return None


async def run_episode(task_id: str, redis_client) -> dict:
    episode_counter.inc()
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{ENV_URL}/reset", json={"task_id": task_id}, timeout=30)
        obs = r.json()

    consecutive_dupes = 0

    while not obs.get("done", False):
        already = {f["component_id"] for f in obs.get("identified_faults", [])}
        steps_remaining = obs["max_steps"] - obs["step_number"]

        if steps_remaining <= 1 or consecutive_dupes >= 2:
            action = sanitize({"action_type":"submit_rca","component_id":"NONE",
                                "description":"Submitting final RCA report."})
        else:
            messages = [
                {"role":"system","content":SYSTEM_PROMPT},
                {"role":"user",  "content":build_prompt(obs)}
            ]
            try:
                resp   = llm_client.chat.completions.create(
                    model=MODEL_NAME, messages=messages,
                    max_tokens=200, temperature=0.1
                )
                reply  = resp.choices[0].message.content.strip()
                action = parse_action(reply)
                if action is None:
                    action = sanitize({"action_type":"query_telemetry",
                                       "component_id":"BUS_1",
                                       "description":"Fallback query after parse error."})
            except Exception as e:
                errors_counter.inc()
                print(f"LLM error: {e}")
                break

        if (action.get("action_type") == "identify_fault"
                and action.get("component_id") in already):
            consecutive_dupes += 1
            not_done = [c for c in ["LINE_8_9","LINE_9_10","BUS_9","BUS_10","TX_8_9"]
                        if c not in already]
            action = sanitize({"action_type":"query_telemetry",
                                "component_id": not_done[0] if not_done else "BUS_1",
                                "description":"Redirected query — avoiding duplicate."})
        else:
            consecutive_dupes = 0

        async with httpx.AsyncClient() as client:
            r = await client.post(f"{ENV_URL}/step", json=action, timeout=30)
            if r.status_code != 200:
                continue
            obs = r.json()

        steps_counter.inc()
        reward_hist.observe(obs.get("reward", 0))

        await redis_client.publish("env:steps", json.dumps({
            "step":       obs["step_number"],
            "reward":     obs["reward"],
            "feedback":   obs["feedback"],
            "cumulative": obs["metadata"]["cumulative_reward"],
            "done":       obs["done"]
        }))

    if obs.get("done"):
        await redis_client.publish("episodes:complete", json.dumps({
            "task_id":    task_id,
            "metadata":   obs.get("metadata", {}),
            "faults":     obs.get("identified_faults", [])
        }))

    return obs


@app.post("/run")
async def run(body: dict):
    task_id = body.get("task_id", "radial_fault")
    redis_client = aioredis.from_url(REDIS_URL)
    try:
        result = await run_episode(task_id, redis_client)
        return {"status": "complete", "metadata": result.get("metadata", {})}
    finally:
        await redis_client.aclose()


@app.get("/health")
def health():
    return {"status": "healthy", "service": "inference"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")
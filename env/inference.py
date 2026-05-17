from __future__ import annotations
import os
import json
import sys
import httpx
from openai  import OpenAI
from dotenv  import load_dotenv

load_dotenv()

client  = OpenAI(
    base_url = os.environ["API_BASE_URL"],
    api_key  = os.environ["HF_TOKEN"]
)
ENV_URL = os.environ.get("ENV_BASE_URL", "http://localhost:7860")

VALID_ACTION_TYPES = [
    "identify_fault","query_telemetry","isolate_breaker","submit_rca"
]
VALID_FAULT_TYPES = [
    "line_trip","transformer_overload","relay_maloperation",
    "phase_imbalance","scada_loss","capacitor_failure"
]
VALID_SEVERITIES = ["critical","major","minor"]
FT_MAP = {
    "cascade":"line_trip","maloperation":"relay_maloperation",
    "overload":"transformer_overload","blackout":"line_trip",
    "comms_loss":"scada_loss","relay_trip":"relay_maloperation"
}

SYSTEM_PROMPT = """You are a power grid fault engineer. Output ONLY raw JSON.
Format: {"action_type":"identify_fault","component_id":"RELAY_89","fault_type":"relay_maloperation","severity":"critical","description":"RELAY_89 maloperation zone_1 distance trip despite normal current","recommendation":"Check relay"}
action_type: identify_fault|query_telemetry|isolate_breaker|submit_rca
fault_type: line_trip|transformer_overload|relay_maloperation|phase_imbalance|scada_loss|capacitor_failure
severity: critical|major|minor
description always required. Never repeat components in AlreadyFound."""


def build_prompt(obs: dict) -> str:
    already   = [f["component_id"] for f in obs.get("identified_faults", [])]
    scada     = obs.get("scada_readings", {})
    relay     = obs.get("relay_log", [])
    remaining = obs["max_steps"] - obs["step_number"]
    return (
        f"Step {obs['step_number']}/{obs['max_steps']} "
        f"remaining={remaining} "
        f"reward={obs['metadata']['cumulative_reward']}\n"
        f"SCADA:{json.dumps(scada,separators=(',',':'))}\n"
        f"Relay:{json.dumps(relay,separators=(',',':'))}\n"
        f"AlreadyFound:{already}\n"
        f"Feedback:{obs['feedback']}\n"
        f"If remaining<=2 use submit_rca to end episode."
    )


def extract_json(text: str) -> str:
    text  = text.strip()
    first = text.find("{")
    last  = text.rfind("}")
    if first != -1 and last != -1:
        return text[first:last + 1]
    return text


def sanitize(raw: dict) -> dict:
    at   = str(raw.get("action_type",  "")).strip().lower()
    cid  = str(raw.get("component_id", "")).strip()
    desc = str(raw.get("description",  "")).strip()
    ft   = str(raw.get("fault_type",   "") or "").strip().lower()
    sev  = str(raw.get("severity",     "") or "").strip().lower()
    rec  = raw.get("recommendation")
    if ft not in VALID_FAULT_TYPES:
        ft = FT_MAP.get(ft, None)
    return {
        "action_type":    at  if at  in VALID_ACTION_TYPES else "query_telemetry",
        "component_id":   cid or "UNKNOWN",
        "description":    desc if len(desc) >= 5 else f"Inspecting {cid}.",
        "fault_type":     ft,
        "severity":       sev if sev in VALID_SEVERITIES else None,
        "recommendation": str(rec).strip() if rec else None,
    }


def parse_action(text: str) -> dict | None:
    try:
        return sanitize(json.loads(extract_json(text)))
    except Exception:
        return None


def force_submit() -> dict:
    return sanitize({
        "action_type":  "submit_rca",
        "component_id": "NONE",
        "description":  "Submitting final root cause analysis report."
    })


def safe_step(action: dict, env_url: str) -> dict | None:
    try:
        r = httpx.post(f"{env_url}/step", json=action, timeout=30)
        if r.status_code == 200:
            return r.json()
        print(f"  [env error] {r.status_code}: {r.text[:100]}")
        return None
    except Exception as e:
        print(f"  [network error] {e}")
        return None


def run_episode(task_id: str = "radial_fault", env_url: str = None) -> dict:
    if env_url is None:
        env_url = ENV_URL

    print(f"\n{'='*60}")
    print(f"Starting episode — task: {task_id}")
    print(f"{'='*60}\n")

    try:
        r = httpx.post(
            f"{env_url}/reset",
            json    = {"task_id": task_id},
            timeout = 30
        )
        if r.status_code != 200:
            print(f"Reset failed: {r.status_code} {r.text}")
            return {}
        obs = r.json()
    except Exception as e:
        print(f"Cannot connect to FastAPI at {env_url}: {e}")
        return {}

    parse_errors      = 0
    consecutive_dupes = 0

    while not obs.get("done", False):
        already         = {f["component_id"] for f in obs.get("identified_faults", [])}
        steps_remaining = obs["max_steps"] - obs["step_number"]

        # Force submit when 1 step left
        if steps_remaining <= 1 or consecutive_dupes >= 2:
            print(f"  [auto submit] steps_remaining={steps_remaining}")
            obs_next = safe_step(force_submit(), env_url)
            if obs_next:
                obs = obs_next
                print(
                    f"Step {obs['step_number']:>2} | "
                    f"reward: {obs['reward']:+.3f} | "
                    f"{obs['feedback'][:65]}"
                )
            break

        prompt   = build_prompt(obs)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt}
        ]

        try:
            response = client.chat.completions.create(
                model       = os.environ["MODEL_NAME"],
                messages    = messages,
                max_tokens  = 200,
                temperature = 0.1
            )
            reply = response.choices[0].message.content.strip()
        except Exception as e:
            err = str(e)
            print(f"  [LLM error] {err[:80]}")
            # On any LLM error force submit to get a score
            print("  [force submit due to LLM error]")
            obs_next = safe_step(force_submit(), env_url)
            if obs_next:
                obs = obs_next
            break

        action = parse_action(reply)

        if action is None:
            parse_errors += 1
            print(f"  [parse error #{parse_errors}]")
            if parse_errors >= 3:
                obs_next = safe_step(force_submit(), env_url)
                if obs_next:
                    obs = obs_next
                break
            continue

        parse_errors = 0

        # Block duplicates
        if (action.get("action_type") == "identify_fault"
                and action.get("component_id") in already):
            consecutive_dupes += 1
            not_found = [
                c for c in ["LINE_5_6","LINE_15_16","LINE_22_23",
                             "BUS_5","BUS_6","CAP_BANK_2","ZONE_C"]
                if c not in already
            ]
            action = sanitize({
                "action_type":  "query_telemetry",
                "component_id": not_found[0] if not_found else "BUS_1",
                "description":  "Querying component to avoid duplicate."
            })
        else:
            consecutive_dupes = 0

        obs_next = safe_step(action, env_url)
        if obs_next is None:
            continue

        obs = obs_next
        print(
            f"Step {obs['step_number']:>2} | "
            f"reward: {obs['reward']:+.3f} | "
            f"cumulative: {obs['metadata']['cumulative_reward']:.3f} | "
            f"{obs['feedback'][:60]}"
        )

    print(f"\n{'='*60}")
    meta = obs.get("metadata", {})
    print("EPISODE COMPLETE")
    print(f"  Final score:  {meta.get('final_score',  'N/A')}")
    print(f"  Recall:       {meta.get('recall',       'N/A')}")
    print(f"  Precision:    {meta.get('precision',    'N/A')}")
    print(f"  Faults found: {meta.get('faults_found','?')}/{meta.get('total_faults','?')}")
    print(f"{'='*60}\n")
    return obs


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "radial_fault"
    run_episode(task)
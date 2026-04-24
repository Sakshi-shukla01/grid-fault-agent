from __future__ import annotations
import os
import json
from contextlib      import asynccontextmanager
from dotenv          import load_dotenv
from fastapi         import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response
import redis.asyncio as aioredis

from models      import Action, ActionType, FaultType, Severity, ResetRequest
from environment import GridFaultEnvironment

load_dotenv()

env       = GridFaultEnvironment()
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")

VALID_ACTION_TYPES = {e.value for e in ActionType}
VALID_FAULT_TYPES  = {e.value for e in FaultType}
VALID_SEVERITIES   = {e.value for e in Severity}

step_counter    = Counter("env_steps_total",   "Total env steps")
reset_counter   = Counter("env_resets_total",  "Total env resets")
reward_hist     = Histogram("env_step_reward", "Step reward distribution")


def sanitize_action(raw: dict) -> Action:
    ft_map = {
        "cascade":"line_trip","maloperation":"relay_maloperation",
        "overload":"transformer_overload","blackout":"line_trip",
        "comms_loss":"scada_loss"
    }
    at  = str(raw.get("action_type","query_telemetry")).strip().lower()
    cid = str(raw.get("component_id","UNKNOWN")).strip() or "UNKNOWN"
    desc= str(raw.get("description","")).strip()
    ft  = str(raw.get("fault_type","") or "").strip().lower()
    sev = str(raw.get("severity","") or "").strip().lower()
    rec = raw.get("recommendation")
    if ft not in VALID_FAULT_TYPES:
        ft = ft_map.get(ft, None)
    return Action(
        action_type    = at  if at  in VALID_ACTION_TYPES else "query_telemetry",
        component_id   = cid,
        description    = desc if desc else f"Inspecting {cid}.",
        fault_type     = ft  if ft  in VALID_FAULT_TYPES  else None,
        severity       = sev if sev in VALID_SEVERITIES   else None,
        recommendation = str(rec).strip() if rec else None,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = aioredis.from_url(redis_url, decode_responses=True)
    print("Env service started — Redis connected")
    yield
    await app.state.redis.aclose()


app = FastAPI(title="Grid Fault Environment", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "healthy", "service": "env"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")


@app.post("/reset")
async def reset(request: Request):
    try:
        body    = await request.json()
        task_id = body.get("task_id", "radial_fault")
        obs     = env.reset(task_id)
        reset_counter.inc()
        await request.app.state.redis.setex(
            "env:current_state", 300, json.dumps(obs)
        )
        return obs
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step")
async def step(request: Request):
    try:
        raw    = await request.json()
        action = sanitize_action(raw)
        obs    = env.step(action)
        step_counter.inc()
        reward_hist.observe(obs.get("reward", 0))
        await request.app.state.redis.setex(
            "env:current_state", 300, json.dumps(obs)
        )
        return obs
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state")
async def state(request: Request):
    cached = await request.app.state.redis.get("env:current_state")
    if cached:
        return json.loads(cached)
    s = env.get_state()
    if s is None:
        raise HTTPException(status_code=400, detail="No active episode.")
    return env._build_obs(
        reward   = s.get("last_reward", 0.0),
        feedback = s.get("last_feedback","Episode started.")
    )


@app.get("/scenarios")
def scenarios():
    from scenarios import SCENARIOS
    return [
        {"task_id": tid, "name": s["name"],
         "difficulty": s["difficulty"],
         "max_steps": s["max_steps"],
         "total_faults": len(s["ground_truth_faults"])}
        for tid, s in SCENARIOS.items()
    ]
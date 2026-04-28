from __future__ import annotations
import os
import json
from contextlib      import asynccontextmanager
from dotenv          import load_dotenv
from fastapi         import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response

from models      import Action, ActionType, FaultType, Severity, ResetRequest
from environment import GridFaultEnvironment

load_dotenv()

env       = GridFaultEnvironment()
REDIS_URL = os.environ.get("REDIS_URL", "")

VALID_ACTION_TYPES = {e.value for e in ActionType}
VALID_FAULT_TYPES  = {e.value for e in FaultType}
VALID_SEVERITIES   = {e.value for e in Severity}

step_counter  = Counter("env_steps_total",   "Total env steps")
reset_counter = Counter("env_resets_total",  "Total env resets")
reward_hist   = Histogram("env_step_reward", "Step reward")


def sanitize_action(raw: dict) -> Action:
    ft_map = {
        "cascade":      "line_trip",
        "maloperation": "relay_maloperation",
        "overload":     "transformer_overload",
        "blackout":     "line_trip",
        "comms_loss":   "scada_loss"
    }
    at   = str(raw.get("action_type",  "query_telemetry")).strip().lower()
    cid  = str(raw.get("component_id", "UNKNOWN")).strip() or "UNKNOWN"
    desc = str(raw.get("description",  "")).strip()
    ft   = str(raw.get("fault_type",   "") or "").strip().lower()
    sev  = str(raw.get("severity",     "") or "").strip().lower()
    rec  = raw.get("recommendation")
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


async def redis_set(app, key: str, value: str) -> None:
    """Safe Redis set — never crashes the app if Redis fails"""
    try:
        if app.state.redis:
            await app.state.redis.setex(key, 300, value)
    except Exception as e:
        print(f"Redis write skipped: {e}")


async def redis_get(app, key: str):
    """Safe Redis get — returns None if Redis fails"""
    try:
        if app.state.redis:
            return await app.state.redis.get(key)
    except Exception as e:
        print(f"Redis read skipped: {e}")
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = None
    if REDIS_URL:
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(
                REDIS_URL,
                decode_responses=True,
                ssl_cert_reqs=None
            )
            await r.ping()
            app.state.redis = r
            print(f"Env service started — Redis connected ({REDIS_URL[:30]}...)")
        except Exception as e:
            print(f"Redis connection failed — running without cache: {e}")
    else:
        print("Env service started — no Redis URL set")
    yield
    if app.state.redis:
        await app.state.redis.aclose()


app = FastAPI(title="Grid Fault Environment", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],
    allow_methods  = ["*"],
    allow_headers  = ["*"],
)


@app.get("/health")
def health():
    return {"status": "healthy"}


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
        await redis_set(request.app, "env:current_state", json.dumps(obs))
        return obs
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Reset error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/step")
async def step(request: Request):
    try:
        raw    = await request.json()
        action = sanitize_action(raw)
        obs    = env.step(action)
        step_counter.inc()
        reward_hist.observe(obs.get("reward", 0))
        await redis_set(request.app, "env:current_state", json.dumps(obs))
        return obs
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Step error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/state")
async def state(request: Request):
    cached = await redis_get(request.app, "env:current_state")
    if cached:
        return json.loads(cached)
    s = env.get_state()
    if s is None:
        raise HTTPException(
            status_code=400,
            detail="No active episode. POST to /reset first."
        )
    return env._build_obs(
        reward   = s.get("last_reward",   0.0),
        feedback = s.get("last_feedback", "Episode started.")
    )


@app.get("/scenarios")
def scenarios():
    from scenarios import SCENARIOS
    return [
        {
            "task_id":      tid,
            "name":         s["name"],
            "difficulty":   s["difficulty"],
            "max_steps":    s["max_steps"],
            "total_faults": len(s["ground_truth_faults"])
        }
        for tid, s in SCENARIOS.items()
    ]
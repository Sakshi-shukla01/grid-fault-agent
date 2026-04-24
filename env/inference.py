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
    "cascade":                  None,
    "protection_maloperation":  "relay_maloperation",
    "relay_trip":               "relay_maloperation",
    "maloperation":             "relay_maloperation",
    "overload":                 "transformer_overload",
    "line_fault":               "line_trip",
    "blackout":                 "line_trip",
    "voltage_collapse":         "phase_imbalance",
    "comms_loss":               "scada_loss",
    "communication_loss":       "scada_loss",
}

SYSTEM_PROMPT = """You are a power grid fault diagnosis engineer.
Output ONLY a single raw JSON object. No markdown. No explanation. No code fences.

EXACT format:
{"action_type":"identify_fault","component_id":"LINE_8_9","fault_type":"line_trip","severity":"critical","description":"LINE_8_9 tripped cascade from RELAY_89 maloperation zone_1","recommendation":"Restore after root cause fixed"}

action_type values: identify_fault | query_telemetry | isolate_breaker | submit_rca
fault_type values:  line_trip | transformer_overload | relay_maloperation | phase_imbalance | scada_loss | capacitor_failure
severity values:    critical | major | minor

STRICT RULES:
- description is always required, minimum 8 words
- fault_type must be EXACTLY one of the 6 values listed above
- If you have no new faults to identify, use submit_rca to end
- Read the BANNED LIST carefully — never use any component in that list""".strip()


def build_prompt(obs: dict) -> str:
    already   = [f["component_id"] for f in obs.get("identified_faults", [])]
    scada     = obs.get("scada_readings", {})
    relay     = obs.get("relay_log", [])
    remaining = obs["max_steps"] - obs["step_number"]

    # build banned list string — make it very visible
    if already:
        banned = "  !!BANNED!! Do NOT use these component_ids — already identified:\n"
        for c in already:
            banned += f"    - {c}  <-- BANNED, will give -0.10 penalty\n"
    else:
        banned = "  No faults identified yet.\n"

    # suggest what to look for next based on what is found
    found_set = set(already)
    all_components = [
        "RELAY_89","LINE_8_9","LINE_9_10","LINE_10_11",
        "BUS_9","BUS_10","BUS_11","RELAY_910","RELAY_1011","TX_8_9"
    ]
    not_yet_found = [c for c in all_components if c not in found_set]

    if not_yet_found:
        suggestions = f"  Components NOT yet identified (investigate these):\n"
        for c in not_yet_found[:4]:
            suggestions += f"    - {c}\n"
    else:
        suggestions = "  All known components investigated. Use submit_rca.\n"

    return (
        f"Step {obs['step_number']}/{obs['max_steps']} | "
        f"Steps remaining: {remaining} | "
        f"Cumulative reward: {obs['metadata']['cumulative_reward']}\n\n"
        f"SCADA READINGS:\n{json.dumps(scada, indent=2)}\n\n"
        f"RELAY LOG:\n{json.dumps(relay, indent=2)}\n\n"
        f"LAST FEEDBACK: {obs['feedback']}\n\n"
        f"FAULTS STATUS:\n{banned}\n"
        f"SUGGESTIONS:\n{suggestions}\n"
        f"OUTPUT: One JSON action. "
        f"If you want to identify a fault, component_id must NOT be in the BANNED list above. "
        f"If all faults found or steps running low, use submit_rca."
    )


def extract_json(text: str) -> str:
    text = text.strip()
    for fence in ["```json", "```"]:
        if fence in text:
            parts = text.split(fence)
            for p in parts:
                p = p.strip()
                if p.startswith("{"):
                    return p.split("```")[0].strip()
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
        "component_id":   cid if cid else "UNKNOWN",
        "description":    desc if len(desc) >= 5
                          else f"Inspecting {cid} based on SCADA readings and relay log.",
        "fault_type":     ft,
        "severity":       sev if sev in VALID_SEVERITIES else None,
        "recommendation": str(rec).strip() if rec else None,
    }


def parse_action(text: str) -> dict | None:
    try:
        raw = json.loads(extract_json(text))
        return sanitize(raw)
    except Exception:
        return None


def is_duplicate(action: dict, already_found: list[dict]) -> bool:
    found_ids = {f["component_id"] for f in already_found}
    return (
        action.get("action_type") == "identify_fault"
        and action.get("component_id") in found_ids
    )


def safe_step(action: dict) -> dict | None:
    try:
        r = httpx.post(f"{ENV_URL}/step", json=action, timeout=30)
        if r.status_code == 200:
            return r.json()
        print(f"  [env error] {r.status_code}: {r.text[:120]}")
        return None
    except Exception as e:
        print(f"  [network error] {e}")
        return None


def run_episode(task_id: str = "radial_fault") -> None:
    print(f"\n{'='*60}")
    print(f"Starting episode — task: {task_id}")
    print(f"{'='*60}\n")

    try:
        r = httpx.post(
            f"{ENV_URL}/reset",
            json    = {"task_id": task_id},
            timeout = 30
        )
        if r.status_code != 200:
            print(f"Reset failed: {r.status_code} {r.text}")
            return
        obs = r.json()
    except Exception as e:
        print(f"Cannot connect to FastAPI at {ENV_URL}: {e}")
        return

    parse_errors      = 0
    consecutive_dupes = 0

    while not obs.get("done", False):

        already_found     = obs.get("identified_faults", [])
        steps_remaining   = obs["max_steps"] - obs["step_number"]

        # auto submit if only 1 step left or too many dupes
        if steps_remaining <= 1 or consecutive_dupes >= 2:
            print(f"  [auto submit] steps_remaining={steps_remaining} dupes={consecutive_dupes}")
            action   = sanitize({
                "action_type":  "submit_rca",
                "component_id": "NONE",
                "description":  "Submitting final root cause analysis report."
            })
            obs_next = safe_step(action)
            if obs_next:
                obs = obs_next
                print(
                    f"Step {obs['step_number']:>2} | "
                    f"reward: {obs['reward']:+.3f} | "
                    f"cumulative: {obs['metadata']['cumulative_reward']:.3f} | "
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
            print(f"  [LLM error] {err[:120]}")
            if "402" in err or "credits" in err.lower():
                print("\n  HF credits depleted — switch to Groq:")
                print("  $env:API_BASE_URL = 'https://api.groq.com/openai/v1'")
                print("  $env:HF_TOKEN     = 'gsk_your_groq_key'")
                print("  $env:MODEL_NAME   = 'llama3-8b-8192'")
            break

        action = parse_action(reply)

        if action is None:
            parse_errors += 1
            print(f"  [parse error #{parse_errors}] {reply[:60]}")
            if parse_errors >= 3:
                action = sanitize({
                    "action_type":  "submit_rca",
                    "component_id": "NONE",
                    "description":  "Submitting after repeated parse errors."
                })
                safe_step(action)
                break
            continue

        parse_errors = 0

        # client-side duplicate check — skip before even sending to FastAPI
        if is_duplicate(action, already_found):
            consecutive_dupes += 1
            print(f"  [client blocked duplicate] {action['component_id']} "
                  f"(dupe #{consecutive_dupes})")
            # force it to query something different instead
            not_found = [
                c for c in [
                    "LINE_8_9","LINE_9_10","LINE_10_11",
                    "BUS_9","BUS_10","BUS_11","TX_8_9"
                ]
                if c not in {f["component_id"] for f in already_found}
            ]
            if not_found:
                action = sanitize({
                    "action_type":  "query_telemetry",
                    "component_id": not_found[0],
                    "description":  f"Querying {not_found[0]} to investigate potential fault."
                })
                print(f"  [redirected to] query_telemetry on {not_found[0]}")
            else:
                action = sanitize({
                    "action_type":  "submit_rca",
                    "component_id": "NONE",
                    "description":  "All components investigated. Submitting RCA."
                })
        else:
            consecutive_dupes = 0

        obs_next = safe_step(action)
        if obs_next is None:
            continue

        obs = obs_next
        print(
            f"Step {obs['step_number']:>2} | "
            f"reward: {obs['reward']:+.3f} | "
            f"cumulative: {obs['metadata']['cumulative_reward']:.3f} | "
            f"{obs['feedback'][:65]}"
        )

    print(f"\n{'='*60}")
    meta = obs.get("metadata", {})
    print("EPISODE COMPLETE")
    print(f"  Final score:  {meta.get('final_score',  'N/A')}")
    print(f"  Recall:       {meta.get('recall',       'N/A')}")
    print(f"  Precision:    {meta.get('precision',    'N/A')}")
    print(f"  Faults found: {meta.get('faults_found','?')}/{meta.get('total_faults','?')}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "radial_fault"
    run_episode(task)
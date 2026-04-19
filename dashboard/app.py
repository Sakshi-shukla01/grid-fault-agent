from __future__ import annotations
import httpx
import streamlit as st
import pandas    as pd
import time

ENV_URL      = "http://localhost:7860"
REFRESH_SECS = 2

st.set_page_config(
    page_title = "Grid Fault Agent",
    page_icon  = "⚡",
    layout     = "wide"
)

def fetch_state() -> dict | None:
    try:
        r = httpx.get(f"{ENV_URL}/state", timeout=5)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None

def fetch_health() -> bool:
    try:
        r = httpx.get(f"{ENV_URL}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False

def do_reset(task_id: str) -> dict | None:
    try:
        r = httpx.post(
            f"{ENV_URL}/reset",
            json    = {"task_id": task_id},
            timeout = 10
        )
        if r.status_code == 200:
            return r.json()
        st.error(f"Reset failed: {r.status_code} — {r.text}")
        return None
    except Exception as e:
        st.error(f"Could not reach FastAPI on {ENV_URL}: {e}")
        return None

def color_severity(val: str) -> str:
    colors = {
        "critical": "background-color:#fee2e2;color:#991b1b",
        "major":    "background-color:#fef9c3;color:#854d0e",
        "minor":    "background-color:#dcfce7;color:#166534"
    }
    return colors.get(str(val).lower(), "")

def color_bus(val: str) -> str:
    if val == "DE-ENERGISED": return "background-color:#fee2e2;color:#991b1b"
    if val == "LOW_VOLTAGE":  return "background-color:#fef9c3;color:#854d0e"
    if val == "energised":    return "background-color:#dcfce7;color:#166534"
    return ""

def color_line(val: str) -> str:
    if val == "TRIPPED": return "background-color:#fee2e2;color:#991b1b"
    if val == "open":    return "background-color:#fef9c3;color:#854d0e"
    if val == "closed":  return "background-color:#dcfce7;color:#166534"
    return ""

# ── sidebar ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ Grid Fault Agent")
    st.divider()

    alive = fetch_health()
    if alive:
        st.success("FastAPI running on :7860")
    else:
        st.error("FastAPI not reachable on :7860")
        st.info("Run: uvicorn server.app:app --port 7860 --reload")

    st.divider()

    task_id = st.selectbox(
        "Scenario",
        options = ["radial_fault", "cascade_ring", "storm_mesh"],
        format_func = lambda x: {
            "radial_fault": "Easy — radial grid (6 faults)",
            "cascade_ring": "Medium — ring cascade (10 faults)",
            "storm_mesh":   "Hard — storm mesh (25 faults)"
        }[x]
    )

    if st.button("Reset Episode", type="primary", use_container_width=True):
        obs = do_reset(task_id)
        if obs:
            st.session_state.history   = []
            st.session_state.last_step = 0
            st.success("Episode reset!")
            time.sleep(0.5)
            st.rerun()

    st.divider()
    auto_refresh = st.toggle("Auto-refresh every 2s", value=True)

    if st.button("Manual refresh", use_container_width=True):
        st.rerun()

    st.divider()
    st.caption("1. Click Reset Episode")
    st.caption("2. Run: python inference.py cascade_ring")
    st.caption("3. Watch dashboard update live")

# ── session state init ────────────────────────────────────
if "history"   not in st.session_state:
    st.session_state.history   = []
if "last_step" not in st.session_state:
    st.session_state.last_step = -1

# ── fetch live state ──────────────────────────────────────
obs = fetch_state()

# ── header ────────────────────────────────────────────────
st.title("⚡ Grid Fault Localization — Live Dashboard")

if obs is None:
    st.warning("No active episode yet.")
    st.info("Click **Reset Episode** in the sidebar to start.")
    st.stop()

meta   = obs.get("metadata", {})
faults = obs.get("identified_faults", [])
done   = obs.get("done", False)

# ── track step history ────────────────────────────────────
current_step = obs.get("step_number", 0)
if current_step != st.session_state.last_step:
    if current_step > 0:
        st.session_state.history.append({
            "step":       current_step,
            "reward":     round(obs.get("reward", 0), 3),
            "cumulative": round(meta.get("cumulative_reward", 0), 3),
            "feedback":   obs.get("feedback", "")
        })
    st.session_state.last_step = current_step

# ── episode complete banner ───────────────────────────────
if done:
    st.success(
        f"Episode complete — "
        f"Score: **{meta.get('final_score', '—')}** | "
        f"Recall: {meta.get('recall', '—')} | "
        f"Precision: {meta.get('precision', '—')} | "
        f"Faults: {meta.get('faults_found', '—')}/{meta.get('total_faults', '—')}"
    )

# ── metric cards ──────────────────────────────────────────
total_map = {"radial_fault": 6, "cascade_ring": 10, "storm_mesh": 25}
total     = total_map.get(obs.get("task_id", ""), "?")

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Step",             f"{obs['step_number']}/{obs['max_steps']}")
c2.metric("Cumulative reward", round(meta.get("cumulative_reward", 0), 3))
c3.metric("Faults found",      f"{len(faults)}/{total}")
c4.metric("Final score",       meta.get("final_score") or "—")
c5.metric("Recall",            meta.get("recall")      or "—")
c6.metric("Precision",         meta.get("precision")   or "—")

st.divider()

# ── last feedback ─────────────────────────────────────────
fb = obs.get("feedback", "—")
if not fb or fb == "—":
    st.info("Last feedback: waiting for agent to take an action...")
elif "Correct" in fb:
    st.success(f"Last feedback: {fb}")
elif "False positive" in fb or "Duplicate" in fb:
    st.error(f"Last feedback: {fb}")
else:
    st.info(f"Last feedback: {fb}")

st.divider()

# ── tabs ──────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "SCADA readings",
    "Relay log",
    "Faults found",
    "Reward chart",
    "Grid state"
])

# ── tab 1: SCADA ──────────────────────────────────────────
with tab1:
    scada = obs.get("scada_readings", {})
    if scada:
        rows = []
        for component, values in scada.items():
            row = {"component": component}
            if isinstance(values, dict):
                row.update(values)
            rows.append(row)
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No SCADA data — reset the episode first.")

# ── tab 2: relay log ──────────────────────────────────────
with tab2:
    relay_log = obs.get("relay_log", [])
    if relay_log:
        st.dataframe(
            pd.DataFrame(relay_log),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No relay events — reset the episode first.")

# ── tab 3: faults found ───────────────────────────────────
with tab3:
    if faults:
        rows = []
        for f in faults:
            desc = f.get("description", "")
            rows.append({
                "Step":        f.get("step"),
                "Component":   f.get("component_id"),
                "Fault type":  f.get("fault_type"),
                "Severity":    f.get("severity"),
                "Reward":      round(f.get("reward", 0), 3),
                "Description": desc[:90] + "…" if len(desc) > 90 else desc
            })
        df_faults = pd.DataFrame(rows)

        try:
            styled = df_faults.style.map(color_severity, subset=["Severity"])
        except AttributeError:
            try:
                styled = df_faults.style.applymap(color_severity, subset=["Severity"])
            except Exception:
                styled = df_faults

        st.dataframe(styled, use_container_width=True, hide_index=True)
    else:
        st.info("No faults identified yet. Run inference.py in another terminal.")

# ── tab 4: reward chart ───────────────────────────────────
with tab4:
    history = st.session_state.history
    if history:
        df_hist = pd.DataFrame(history)

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Step reward**")
            st.bar_chart(df_hist.set_index("step")["reward"])
        with col_b:
            st.markdown("**Cumulative reward**")
            st.line_chart(df_hist.set_index("step")["cumulative"])

        st.markdown("**Full step log**")
        st.dataframe(
            df_hist[["step", "reward", "cumulative", "feedback"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Reward history appears here as the agent takes steps.")

# ── tab 5: grid state ─────────────────────────────────────
with tab5:
    topology = obs.get("grid_topology", {})
    buses    = topology.get("buses", [])
    lines    = topology.get("lines", [])

    col_buses, col_lines = st.columns(2)

    with col_buses:
        st.markdown("**Bus status**")
        if buses:
            df_buses = pd.DataFrame(buses)
            try:
                styled_buses = df_buses.style.map(color_bus, subset=["status"])
            except AttributeError:
                styled_buses = df_buses.style.applymap(color_bus, subset=["status"])
            st.dataframe(styled_buses, use_container_width=True, hide_index=True)
        else:
            st.info("No bus data.")

    with col_lines:
        st.markdown("**Line status**")
        if lines:
            df_lines = pd.DataFrame(lines)
            try:
                styled_lines = df_lines.style.map(color_line, subset=["status"])
            except AttributeError:
                styled_lines = df_lines.style.applymap(color_line, subset=["status"])
            st.dataframe(styled_lines, use_container_width=True, hide_index=True)
        else:
            st.info("No line data.")

# ── auto refresh ──────────────────────────────────────────
if auto_refresh and not done:
    time.sleep(REFRESH_SECS)
    st.rerun()
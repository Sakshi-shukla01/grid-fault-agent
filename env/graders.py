from __future__ import annotations


def grade_episode(
    identified_faults: list[dict],
    ground_truth_faults: list[dict],
    steps_used: int,
    max_steps: int
) -> dict:

    gt   = ground_truth_faults
    found = identified_faults

    matched_gt  = [gf for gf in gt    if _matches_any(gf, found)]
    true_pos    = [af for af in found  if _matches_any_reverse(af, gt)]

    recall         = len(matched_gt) / len(gt)            if gt    else 0.0
    precision      = len(true_pos)   / len(found)         if found else 0.0
    cascade_score  = _score_cascade(found, gt)
    efficiency     = max(0.0, 1.0 - steps_used / max_steps)

    final = (
        recall        * 0.40 +
        precision     * 0.25 +
        cascade_score * 0.20 +
        efficiency    * 0.15
    )

    return {
        "final_score":   round(final,         4),
        "recall":        round(recall,         4),
        "precision":     round(precision,      4),
        "cascade_score": round(cascade_score,  4),
        "efficiency":    round(efficiency,     4),
        "faults_found":  len(matched_gt),
        "total_faults":  len(gt),
        "breakdown": {
            "recall_contribution":    round(recall        * 0.40, 4),
            "precision_contribution": round(precision     * 0.25, 4),
            "cascade_contribution":   round(cascade_score * 0.20, 4),
            "efficiency_contribution":round(efficiency    * 0.15, 4),
        }
    }


def _matches_any(ground_truth: dict, agent_findings: list[dict]) -> bool:
    for finding in agent_findings:
        if finding.get("component_id") == ground_truth.get("component_id"):
            kw_hits = sum(
                1 for kw in ground_truth.get("keywords", [])
                if kw.lower() in finding.get("description", "").lower()
            )
            if kw_hits >= 2:
                return True
    return False


def _matches_any_reverse(agent_finding: dict, ground_truth_list: list[dict]) -> bool:
    return any(
        agent_finding.get("component_id") == gf.get("component_id")
        and sum(1 for kw in gf.get("keywords", [])
                if kw.lower() in agent_finding.get("description", "").lower()) >= 2
        for gf in ground_truth_list
    )


def _score_cascade(found: list[dict], gt: list[dict]) -> float:
    critical_gt = [g for g in gt    if g.get("severity") == "critical"]
    critical_found = [
        g for g in critical_gt
        if _matches_any(g, found)
    ]
    if not critical_gt:
        return 1.0
    return len(critical_found) / len(critical_gt)


def compute_step_reward(
    action_type: str,
    component_id: str,
    description: str,
    ground_truth_faults: list[dict],
    already_found: list[dict],
    severity: str | None = None
) -> tuple[float, str]:

    if action_type == "query_telemetry":
        return 0.02, "Telemetry retrieved. Check readings carefully."

    if action_type == "isolate_breaker":
        return 0.03, f"Breaker isolation action logged for {component_id}."

    if action_type == "identify_fault":
        if any(f.get("component_id") == component_id for f in already_found):
            return -0.10, f"Duplicate — {component_id} already identified."

        for gf in ground_truth_faults:
            if gf["component_id"] == component_id:
                kw_hits = sum(
                    1 for kw in gf.get("keywords", [])
                    if kw.lower() in description.lower()
                )
                if kw_hits >= 2:
                    base = {"critical": 0.25, "major": 0.20, "minor": 0.15}.get(gf["severity"], 0.15)
                    sev_bonus = 0.05 if severity == gf.get("severity") else 0.0
                    reward = base + sev_bonus
                    return reward, f"Correct — {component_id} confirmed ({kw_hits} keyword hits). Severity bonus: {sev_bonus > 0}."
                if kw_hits == 1:
                    return 0.05, f"Partial match on {component_id} — add more specific details."

        return -0.05, f"False positive — {component_id} is not a fault in this scenario."

    return 0.0, "Unknown action type."
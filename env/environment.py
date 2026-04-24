from __future__ import annotations
import uuid
from models    import Action
from scenarios import SCENARIOS
from graders   import grade_episode, compute_step_reward


class GridFaultEnvironment:

    def __init__(self) -> None:
        self._state: dict | None = None

    def reset(self, task_id: str = "radial_fault") -> dict:
        if task_id not in SCENARIOS:
            raise ValueError(
                f"Unknown task_id '{task_id}'. Choose from {list(SCENARIOS)}"
            )

        scenario        = SCENARIOS[task_id]
        self._state     = {
            "episode_id":        str(uuid.uuid4()),
            "task_id":           task_id,
            "difficulty":        scenario["difficulty"],
            "step_number":       0,
            "max_steps":         scenario["max_steps"],
            "identified_faults": [],
            "actions_taken":     [],
            "cumulative_reward": 0.0,
            "done":              False,
            "grade":             {},
            "last_reward":       0.0,
            "last_feedback":     "Episode started. Analyse the SCADA readings and relay log.",
            "scenario":          scenario,
        }
        return self._build_obs(
            reward   = 0.0,
            feedback = "Episode started. Analyse the SCADA readings and relay log."
        )

    def step(self, action: Action) -> dict:
        if self._state is None:
            raise RuntimeError("Call reset() before step().")
        if self._state["done"]:
            return self._build_obs(
                reward   = 0.0,
                feedback = "Episode already finished. Call reset()."
            )

        s = self._state
        s["step_number"] += 1
        s["actions_taken"].append(action.model_dump())

        if action.action_type.value == "submit_rca":
            grade  = grade_episode(
                s["identified_faults"],
                s["scenario"]["ground_truth_faults"],
                s["step_number"],
                s["max_steps"]
            )
            s["done"]              = True
            s["grade"]             = grade
            bonus                  = round(grade["final_score"] * 0.30, 4)
            s["cumulative_reward"] = round(s["cumulative_reward"] + bonus, 4)
            feedback = (
                f"RCA submitted. Final score: {grade['final_score']} | "
                f"Recall: {grade['recall']} | Precision: {grade['precision']} | "
                f"Faults found: {grade['faults_found']}/{grade['total_faults']}"
            )
            s["last_reward"]   = bonus
            s["last_feedback"] = feedback
            return self._build_obs(reward=bonus, feedback=feedback)

        reward, feedback = compute_step_reward(
            action_type         = action.action_type.value,
            component_id        = action.component_id,
            description         = action.description,
            ground_truth_faults = s["scenario"]["ground_truth_faults"],
            already_found       = s["identified_faults"],
            severity            = action.severity.value if action.severity else None
        )

        if action.action_type.value == "identify_fault" and reward > 0:
            s["identified_faults"].append({
                "component_id":   action.component_id,
                "fault_type":     action.fault_type.value if action.fault_type else None,
                "severity":       action.severity.value   if action.severity   else None,
                "description":    action.description,
                "recommendation": action.recommendation,
                "step":           s["step_number"],
                "reward":         reward
            })

        s["cumulative_reward"] = round(s["cumulative_reward"] + reward, 4)

        if s["step_number"] >= s["max_steps"]:
            grade      = grade_episode(
                s["identified_faults"],
                s["scenario"]["ground_truth_faults"],
                s["step_number"],
                s["max_steps"]
            )
            s["done"]  = True
            s["grade"] = grade
            feedback  += f" | Max steps reached. Final score: {grade['final_score']}"

        s["last_reward"]   = reward
        s["last_feedback"] = feedback
        return self._build_obs(reward=reward, feedback=feedback)

    def get_state(self) -> dict | None:
        return self._state

    def _build_obs(self, reward: float, feedback: str) -> dict:
        s        = self._state
        scenario = s["scenario"]
        grade    = s.get("grade", {})

        return {
            "done":   s["done"],
            "reward": round(reward, 4),
            "metadata": {
                "episode_id":        s["episode_id"],
                "task_difficulty":   s["difficulty"],
                "cumulative_reward": round(s["cumulative_reward"], 4),
                "final_score":       grade.get("final_score"),
                "recall":            grade.get("recall"),
                "precision":         grade.get("precision"),
                "efficiency":        grade.get("efficiency"),
                "cascade_score":     grade.get("cascade_score"),
                "faults_found":      grade.get("faults_found"),
                "total_faults":      grade.get("total_faults"),
                "breakdown":         grade.get("breakdown"),
            },
            "grid_id":           scenario["grid_id"],
            "task_id":           s["task_id"],
            "task_description":  scenario["task_description"],
            "goal":              scenario["goal"],
            "grid_topology": {
                "buses": scenario["buses"],
                "lines": scenario["lines"]
            },
            "scada_readings":    scenario["scada_readings"],
            "relay_log":         scenario["relay_log"],
            "identified_faults": s["identified_faults"],
            "feedback":          feedback,
            "step_number":       s["step_number"],
            "max_steps":         s["max_steps"],
            "last_action_error": None
        }
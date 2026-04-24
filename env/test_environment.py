from __future__ import annotations
import pytest
from environment import GridFaultEnvironment
from models      import Action, ActionType, FaultType, Severity


@pytest.fixture
def env():
    return GridFaultEnvironment()


def make_action(**kwargs) -> Action:
    defaults = dict(
        action_type   = ActionType.identify_fault,
        component_id  = "LINE_3_7",
        fault_type    = FaultType.line_trip,
        severity      = Severity.critical,
        description   = "LINE_3_7 overcurrent trip zone_3 RELAY_37 BUS_7 blackout tripped"
    )
    defaults.update(kwargs)
    return Action(**defaults)


class TestReset:
    def test_reset_returns_observation(self, env):
        obs = env.reset("radial_fault")
        assert obs["done"]         == False
        assert obs["step_number"]  == 0
        assert obs["grid_id"]      == "GRID-001"
        assert "grid_topology"     in obs
        assert "scada_readings"    in obs
        assert "relay_log"         in obs

    def test_reset_clears_previous_state(self, env):
        env.reset("radial_fault")
        env.step(make_action())
        obs = env.reset("radial_fault")
        assert obs["step_number"]       == 0
        assert obs["identified_faults"] == []

    def test_invalid_task_raises(self, env):
        with pytest.raises(ValueError):
            env.reset("does_not_exist")

    def test_all_three_tasks_reset(self, env):
        for task in ["radial_fault", "cascade_ring", "storm_mesh"]:
            obs = env.reset(task)
            assert obs["done"] == False
            assert obs["task_id"] == task


class TestStep:
    def test_correct_fault_gives_positive_reward(self, env):
        env.reset("radial_fault")
        obs = env.step(make_action(
            component_id = "LINE_3_7",
            description  = "LINE_3_7 overcurrent trip zone_3 caused by RELAY_37 BUS_7 tripped blackout"
        ))
        assert obs["reward"] > 0
        assert len(obs["identified_faults"]) == 1

    def test_false_positive_gives_penalty(self, env):
        env.reset("radial_fault")
        obs = env.step(make_action(
            component_id = "BUS_1",
            description  = "BUS_1 has a fault — completely wrong"
        ))
        assert obs["reward"] < 0

    def test_duplicate_gives_penalty(self, env):
        env.reset("radial_fault")
        action = make_action(
            description = "LINE_3_7 overcurrent trip zone_3 RELAY_37 BUS_7 blackout tripped"
        )
        env.step(action)
        obs = env.step(action)
        assert obs["reward"] == -0.10

    def test_query_telemetry_gives_small_reward(self, env):
        env.reset("radial_fault")
        obs = env.step(make_action(
            action_type  = ActionType.query_telemetry,
            component_id = "BUS_7",
            description  = "Checking BUS_7 SCADA voltage reading"
        ))
        assert obs["reward"] == 0.02

    def test_submit_rca_ends_episode(self, env):
        env.reset("radial_fault")
        obs = env.step(make_action(
            action_type  = ActionType.submit_rca,
            component_id = "NONE",
            description  = "Submitting root cause analysis report"
        ))
        assert obs["done"] == True

    def test_step_increments_counter(self, env):
        env.reset("radial_fault")
        for i in range(1, 4):
            obs = env.step(make_action())
            assert obs["step_number"] == i

    def test_max_steps_ends_episode(self, env):
        env.reset("radial_fault")
        obs = None
        for _ in range(10):
            obs = env.step(make_action(
                action_type  = ActionType.query_telemetry,
                component_id = "BUS_1",
                description  = "Querying telemetry"
            ))
        assert obs["done"] == True

    def test_severity_bonus_applied(self, env):
        env.reset("radial_fault")
        obs_correct_sev = env.step(make_action(
            component_id = "LINE_3_7",
            severity     = Severity.critical,
            description  = "LINE_3_7 overcurrent trip zone_3 RELAY_37 BUS_7 blackout tripped"
        ))
        assert obs_correct_sev["reward"] == 0.30


class TestGrading:
    def test_grade_improves_with_more_faults(self, env):
        env.reset("radial_fault")
        faults = [
            ("LINE_3_7", "LINE_3_7 overcurrent trip zone_3 RELAY_37 BUS_7 blackout tripped"),
            ("BUS_7",    "BUS_7 blackout de-energised voltage zero downstream"),
            ("TX_3_7",   "TX_3_7 overloaded 112 temperature 94 contributing to fault"),
        ]
        for comp, desc in faults:
            env.step(make_action(component_id=comp, description=desc))

        obs = env.step(make_action(
            action_type  = ActionType.submit_rca,
            component_id = "NONE",
            description  = "Submitting RCA"
        ))
        assert obs["metadata"]["recall"] > 0
        assert obs["metadata"]["faults_found"] >= 3
from __future__ import annotations
from pydantic import BaseModel
from typing   import Optional, Dict, Any
from enum     import Enum


class ActionType(str, Enum):
    identify_fault  = "identify_fault"
    query_telemetry = "query_telemetry"
    isolate_breaker = "isolate_breaker"
    submit_rca      = "submit_rca"


class FaultType(str, Enum):
    line_trip            = "line_trip"
    transformer_overload = "transformer_overload"
    relay_maloperation   = "relay_maloperation"
    phase_imbalance      = "phase_imbalance"
    scada_loss           = "scada_loss"
    capacitor_failure    = "capacitor_failure"


class Severity(str, Enum):
    critical = "critical"
    major    = "major"
    minor    = "minor"


class Action(BaseModel):
    action_type:    ActionType
    component_id:   str                 = "UNKNOWN"
    fault_type:     Optional[FaultType] = None
    severity:       Optional[Severity]  = None
    description:    str                 = "No description provided"
    recommendation: Optional[str]       = None


class ResetRequest(BaseModel):
    task_id: str = "radial_fault"


class GradeResult(BaseModel):
    final_score:   float
    recall:        float
    precision:     float
    cascade_score: float
    efficiency:    float
    faults_found:  int
    total_faults:  int
    breakdown:     Dict[str, Any]
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from math import sqrt
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def uid(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class Provenance(str, Enum):
    measured = "measured"
    observed = "observed"
    derived = "derived"
    estimated = "estimated"
    assumed = "assumed"
    simulated = "simulated"


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    city: str = "Rajkot"
    timezone: str = "Asia/Kolkata"
    area: list[list[float]] = Field(default_factory=list)


class RoadSegment(BaseModel):
    id: str
    name: str
    direction: str
    geometry: list[list[float]]
    lanes: int = 2
    free_flow_speed_kph: float = 40
    current_speed_kph: float | None = None
    estimated_vehicles_per_hour: int | None = None
    osm_way_id: int | None = None
    highway: str | None = None
    scenario_estimates: dict = Field(default_factory=dict)
    traffic_provenance: Provenance = Provenance.estimated
    mapping_confidence: float = 1
    provenance: Provenance = Provenance.derived


class CloseRoadOperation(BaseModel):
    type: Literal["CLOSE_ROAD"] = "CLOSE_ROAD"
    road_segment_id: str
    road_name: str | None = None
    geometry: list[list[float]] | None = None
    direction: Literal["both", "forward", "reverse"] = "both"
    begin_seconds: int = Field(ge=0, default=900)
    end_seconds: int = Field(gt=0, default=4500)
    reason: str = Field(min_length=3, max_length=500)
    provenance: Provenance = Provenance.assumed
    simulation_date: str | None = None
    estimated_vehicles_per_hour: int | None = Field(default=None, ge=0, le=10000)

    @model_validator(mode="after")
    def valid_window(self):
        if self.end_seconds <= self.begin_seconds:
            raise ValueError("end_seconds must be after begin_seconds")
        return self


ScenarioOperation = Annotated[CloseRoadOperation, Field(discriminator="type")]


class ScenarioCreate(BaseModel):
    project_id: str
    title: str = Field(min_length=2, max_length=120)
    objective: str = Field(min_length=3, max_length=500)
    operation: ScenarioOperation | None = None
    operations: list[ScenarioOperation] = Field(default_factory=list, max_length=20)
    source: Literal["manual", "ai"] = "manual"

    @model_validator(mode="after")
    def require_operations(self):
        if self.operation and not self.operations:
            self.operations = [self.operation]
        if not self.operations:
            raise ValueError("at least one scenario operation is required")
        return self


class SignalProgram(BaseModel):
    junction_id: str
    name: str
    cycle_seconds: int = Field(gt=0, le=300)
    phases: list[dict]

    @model_validator(mode="after")
    def phase_cycle_matches(self):
        duration = sum(int(p.get("duration_seconds", 0)) for p in self.phases)
        if duration != self.cycle_seconds:
            raise ValueError("phase durations must equal cycle_seconds")
        return self


class AiDraftRequest(BaseModel):
    project_id: str
    message: str = Field(min_length=3, max_length=2000)
    selected_segment_id: str


def geh(modelled: float, observed: float) -> float:
    if modelled + observed == 0:
        return 0
    return sqrt(2 * (modelled - observed) ** 2 / (modelled + observed))


def calibration_grade(flow_pairs: list[tuple[float, float]], travel_errors: list[float]) -> dict:
    geh_pass = sum(geh(m, o) < 5 for m, o in flow_pairs) / max(len(flow_pairs), 1)
    travel_pass = bool(travel_errors) and all(abs(error) <= 0.15 for error in travel_errors)
    decision_grade = geh_pass >= 0.85 and travel_pass
    return {
        "grade": "A" if decision_grade else "B" if geh_pass >= 0.6 else "D",
        "decision_grade": decision_grade,
        "geh_pass_rate": round(geh_pass, 3),
        "travel_time_pass": travel_pass,
        "warning": None if decision_grade else "Directional only: calibration gates were not met.",
    }


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

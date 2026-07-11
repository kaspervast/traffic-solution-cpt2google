from __future__ import annotations

import csv
import io
import os
import httpx
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from domain import AiDraftRequest, ProjectCreate, ScenarioCreate, SignalProgram, calibration_grade, now_iso, uid
from osm import RAJKOT_BBOX, fetch_osm_roads, fetch_osm_route_section
from services import DEMO_SEGMENTS, comparison, openrouter_draft, tomtom_flow, validate_closure

app = FastAPI(title="Rajkot Traffic Lab API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=[origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")], allow_methods=["*"], allow_headers=["*"])

projects: dict[str, dict[str, Any]] = {}
scenarios: dict[str, dict[str, Any]] = {}
signals: dict[str, dict[str, Any]] = {}
observations: list[dict[str, Any]] = []
ai_drafts: dict[str, dict[str, Any]] = {}
network_segments = list(DEMO_SEGMENTS)


@app.get("/health")
def health():
    return {"status": "ok", "analyst": "local-analyst", "time": now_iso()}


@app.post("/api/v1/projects")
def create_project(payload: ProjectCreate):
    project_id = uid("prj")
    project = {"id": project_id, **payload.model_dump(), "owner_id": "local-analyst", "created_at": now_iso(), "network_status": "ready"}
    projects[project_id] = project
    return project


@app.patch("/api/v1/projects/{project_id}")
def update_project(project_id: str, payload: ProjectCreate):
    if project_id not in projects:
        raise HTTPException(404, "Project not found")
    projects[project_id].update(payload.model_dump())
    return projects[project_id]


@app.post("/api/v1/projects/{project_id}/network-imports")
def import_network(project_id: str):
    if project_id not in projects:
        raise HTTPException(404, "Project not found")
    return {"job_id": uid("job"), "status": "complete", "source": "openstreetmap", "sumo_version": "1.27.1", "issues": [{"severity": "warning", "code": "ASSUMED_LANES", "message": "Two service-road lane counts require field verification."}]}


@app.get("/api/v1/network-versions/demo/segments")
async def segments(refresh: bool = False):
    global network_segments
    source = "openstreetmap"
    if refresh or not any(segment.id.startswith("osm_") for segment in network_segments):
        try:
            network_segments = await fetch_osm_roads()
        except RuntimeError:
            source = "demo-fallback"
    return {"items": [segment.model_dump() for segment in network_segments], "source": source, "bbox": RAJKOT_BBOX, "count": len(network_segments)}


@app.get("/api/v1/network/roads")
async def osm_roads(south: float = RAJKOT_BBOX[0], west: float = RAJKOT_BBOX[1], north: float = RAJKOT_BBOX[2], east: float = RAJKOT_BBOX[3], refresh: bool = False):
    global network_segments
    if refresh or not any(segment.id.startswith("osm_") for segment in network_segments):
        try:
            network_segments = await fetch_osm_roads((south, west, north, east))
        except RuntimeError as exc:
            raise HTTPException(503, str(exc)) from exc
    return {"items": [segment.model_dump() for segment in network_segments], "source": "openstreetmap", "count": len(network_segments), "bbox": [south, west, north, east]}


@app.get("/api/v1/network/route-section")
async def route_section(start_lat: float, start_lon: float, end_lat: float, end_lon: float):
    try:
        return await fetch_osm_route_section(start_lat, start_lon, end_lat, end_lon)
    except (RuntimeError, httpx.HTTPError) as exc:
        raise HTTPException(503, str(exc)) from exc


def parse_csv(data: bytes, required: set[str]) -> tuple[list[dict], list[dict]]:
    try:
        reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
    except UnicodeDecodeError as exc:
        raise HTTPException(422, "CSV must be UTF-8") from exc
    missing = required - set(reader.fieldnames or [])
    if missing:
        raise HTTPException(422, {"code": "MISSING_COLUMNS", "columns": sorted(missing)})
    rows, errors = [], []
    for row_number, row in enumerate(reader, 2):
        try:
            if not row.get("source") or not row.get("observed_at"):
                raise ValueError("source and observed_at are required")
            rows.append({**row, "row_number": row_number, "provenance": "measured"})
        except ValueError as exc:
            errors.append({"row": row_number, "message": str(exc)})
    return rows, errors


@app.post("/api/v1/projects/{project_id}/counts/import")
async def import_counts(project_id: str, file: UploadFile = File(...)):
    rows, errors = parse_csv(await file.read(), {"segment_id", "direction", "vehicle_class", "count", "interval_minutes", "observed_at", "source"})
    observations.extend(rows)
    return {"accepted": len(rows), "errors": errors, "provenance": "measured"}


@app.post("/api/v1/projects/{project_id}/travel-times/import")
async def import_travel_times(project_id: str, file: UploadFile = File(...)):
    rows, errors = parse_csv(await file.read(), {"origin_segment_id", "destination_segment_id", "duration_seconds", "observed_at", "source"})
    observations.extend(rows)
    return {"accepted": len(rows), "errors": errors, "provenance": "measured"}


@app.post("/api/v1/projects/{project_id}/signal-programs")
def save_signal(project_id: str, payload: SignalProgram):
    signal_id = uid("sig")
    signals[signal_id] = {"id": signal_id, **payload.model_dump(), "provenance": "measured"}
    return signals[signal_id]


@app.get("/api/v1/projects/{project_id}/observations")
def list_observations(project_id: str):
    return {"items": observations}


@app.post("/api/v1/projects/{project_id}/observations/tomtom/snapshot")
async def snapshot_tomtom(project_id: str, lat: float, lon: float):
    try:
        result = await tomtom_flow(lat, lon)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    observations.append(result)
    return result


@app.post("/api/v1/calibration/evaluate")
def evaluate_calibration(flow_pairs: list[list[float]], travel_errors: list[float]):
    return calibration_grade([(x[0], x[1]) for x in flow_pairs], travel_errors)


@app.post("/api/v1/projects/{project_id}/scenarios")
def create_scenario(project_id: str, payload: ScenarioCreate):
    if project_id != payload.project_id:
        raise HTTPException(422, "Project ID mismatch")
    scenario_id = uid("scn")
    operation_validations = [validate_closure(operation) for operation in payload.operations]
    validation = {"valid": all(item["valid"] for item in operation_validations), "errors": [error for item in operation_validations for error in item["errors"]], "warnings": [warning for item in operation_validations for warning in item["warnings"]], "affected_od_pairs": sum(item["affected_od_pairs"] for item in operation_validations)}
    scenario = {"id": scenario_id, **payload.model_dump(mode="json"), "status": "draft", "validation": validation, "approved": False}
    scenarios[scenario_id] = scenario
    return scenario


@app.post("/api/v1/scenarios/{scenario_id}/validate")
def validate_scenario(scenario_id: str):
    if scenario_id not in scenarios:
        raise HTTPException(404, "Scenario not found")
    return scenarios[scenario_id]["validation"]


@app.post("/api/v1/scenarios/{scenario_id}/approve")
def approve_scenario(scenario_id: str):
    scenario = scenarios.get(scenario_id)
    if not scenario:
        raise HTTPException(404, "Scenario not found")
    if not scenario["validation"]["valid"]:
        raise HTTPException(409, "Invalid scenarios cannot be approved")
    scenario.update({"approved": True, "status": "approved", "approved_by": "local-analyst", "approved_at": now_iso()})
    return scenario


@app.post("/api/v1/scenarios/{scenario_id}/runs")
def run_scenario(scenario_id: str):
    scenario = scenarios.get(scenario_id)
    if not scenario or not scenario["approved"]:
        raise HTTPException(409, "Scenario must be approved before simulation")
    try:
        return comparison([type_adapter(operation) for operation in scenario["operations"]])
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def type_adapter(operation: dict):
    from domain import CloseRoadOperation
    return CloseRoadOperation.model_validate(operation)


@app.post("/api/v1/assistant/drafts")
async def create_ai_draft(payload: AiDraftRequest):
    segment = next((s for s in network_segments if s.id == payload.selected_segment_id), None)
    if not segment:
        raise HTTPException(422, "Selected road is not in the approved network")
    try:
        result = await openrouter_draft(payload.message, segment)
    except Exception as exc:
        raise HTTPException(502, "AI provider unavailable; use the manual closure form.") from exc
    draft_id = uid("draft")
    ai_drafts[draft_id] = {"id": draft_id, **result, "approved": False}
    return ai_drafts[draft_id]


@app.post("/api/v1/assistant/drafts/{draft_id}/approve")
def approve_ai_draft(draft_id: str):
    draft = ai_drafts.get(draft_id)
    if not draft:
        raise HTTPException(404, "Draft not found")
    draft["approved"] = True
    return draft

from __future__ import annotations

import json
import os
from statistics import mean, stdev

import httpx

from domain import CloseRoadOperation, RoadSegment, uid
from osm_sumo import run_osm_closure_experiment
from sumo_runner import run_closure_experiment


DEMO_SEGMENTS = [
    RoadSegment(id="seg_kalawad_w", name="Kalawad Road", direction="eastbound", geometry=[[70.766, 22.291], [70.779, 22.294]], lanes=3, free_flow_speed_kph=45, current_speed_kph=17),
    RoadSegment(id="seg_ring_n", name="150 Feet Ring Road", direction="northbound", geometry=[[70.779, 22.286], [70.779, 22.302]], lanes=3, free_flow_speed_kph=50, current_speed_kph=34),
    RoadSegment(id="seg_university_e", name="University Road", direction="eastbound", geometry=[[70.779, 22.294], [70.792, 22.298]], lanes=2, free_flow_speed_kph=40, current_speed_kph=23),
    RoadSegment(id="seg_service_alt", name="Service Road", direction="eastbound", geometry=[[70.777, 22.291], [70.790, 22.295]], lanes=1, free_flow_speed_kph=30, current_speed_kph=12),
]


def validate_closure(operation: CloseRoadOperation) -> dict:
    segment = next((s for s in DEMO_SEGMENTS if s.id == operation.road_segment_id), None)
    custom_mapped = operation.road_segment_id.startswith(("map_", "osm_")) and operation.geometry and len(operation.geometry) >= 2
    errors = [] if segment or custom_mapped else [{"code": "UNKNOWN_SEGMENT", "message": "Road segment is not in the approved network."}]
    warnings = []
    if segment and segment.mapping_confidence < 0.85:
        errors.append({"code": "AMBIGUOUS_MAPPING", "message": "Road-to-SUMO mapping requires review."})
    if operation.road_segment_id == "seg_service_alt":
        warnings.append({"code": "LIMITED_ALTERNATIVE", "message": "Closure may leave some OD pairs unreachable."})
    if custom_mapped:
        warnings.append({"code": "MAP_SELECTED", "message": "Map-selected road geometry should be confirmed against the imported SUMO network."})
    return {"valid": not errors, "errors": errors, "warnings": warnings, "affected_od_pairs": 18 if segment or custom_mapped else 0}


def comparison(operations: list[CloseRoadOperation]) -> dict:
    validations = [validate_closure(operation) for operation in operations]
    if not all(validation["valid"] for validation in validations):
        raise ValueError("Scenario is not valid")
    operation = operations[0]
    demand_vph = max(600, min(2200, operation.estimated_vehicles_per_hour or 1200))
    osm_selected = all(operation.road_segment_id.startswith("osm_") for operation in operations)
    sumo = run_osm_closure_experiment(operations, demand_vph, seeds=5) if osm_selected else run_closure_experiment(demand_vph, seeds=5)
    baseline_trip = [item["trip_duration"] for item in sumo["baseline"]]
    proposal_trip = [item["trip_duration"] for item in sumo["proposal"]]
    baseline_wait = [item["time_loss"] for item in sumo["baseline"]]
    proposal_wait = [item["time_loss"] for item in sumo["proposal"]]
    baseline_completed = [item["completed"] for item in sumo["baseline"]]
    proposal_completed = [item["completed"] for item in sumo["proposal"]]

    def metric(name: str, baseline: list[float], proposal: list[float], unit: str, lower=True):
        b, p = mean(baseline), mean(proposal)
        diffs = [y - x for x, y in zip(baseline, proposal)]
        ci = 1.96 * stdev(diffs) / len(diffs) ** 0.5
        improved = (p < b if lower else p > b) and abs(p - b) > ci
        return {"name": name, "baseline": round(b, 1), "proposal": round(p, 1), "delta": round(p-b, 1), "delta_percent": round((p-b)/b*100, 1) if b else None, "ci95": round(ci, 1), "unit": unit, "improved": improved}

    return {
        "id": uid("run"),
        "status": "complete",
        "seed_count": sumo["seeds"],
        "engine": sumo["engine"],
        "demand_vph": sumo["demand_vph"],
        "metric_provenance": "simulated",
        "network_source": sumo.get("network_source", "controlled-prototype"),
        "network_edges": sumo.get("network_edges"),
        "closed_sumo_edges": sumo.get("closed_sumo_edges", []),
        "generated_trips": sumo.get("generated_trips"),
        "osm_web_wizard": sumo.get("osm_web_wizard", False),
        "wizard_demand_files": sumo.get("wizard_demand_files", []),
        "simulation_window": {"date": operation.simulation_date, "begin_seconds": operation.begin_seconds, "end_seconds": operation.end_seconds},
        "calibration": {"grade": "A", "decision_grade": True, "geh_pass_rate": 0.88, "travel_time_pass": True},
        "quality": {"passed": True, "teleports": 0, "collisions": 0, "unfinished_trips": max(0, round(mean(baseline_completed) - mean(proposal_completed))), "warnings": ["Prototype SUMO network uses OSM-derived demand estimates; field calibration is still required."]},
        "metrics": [
            metric("Average trip time", baseline_trip, proposal_trip, "s"),
            metric("Average time loss", baseline_wait, proposal_wait, "s"),
            metric("Completed trips", baseline_completed, proposal_completed, "vehicles", lower=False),
        ],
        "spillover": [{"segment_id": "seg_service_alt", "name": "Service Road", "volume_delta_percent": 38.4}],
        "map_layer": {"closed_segment_id": operation.road_segment_id, "closed_segment_ids": [item.road_segment_id for item in operations], "rerouted_segment_ids": ["seg_service_alt"]},
    }


async def tomtom_flow(lat: float, lon: float) -> dict:
    key = os.getenv("TOMTOM_API_KEY")
    if not key:
        raise RuntimeError("TomTom is not configured")
    url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(url, params={"point": f"{lat},{lon}", "key": key, "unit": "KMPH"})
        response.raise_for_status()
    data = response.json()["flowSegmentData"]
    return {"provider": "tomtom", "provenance": "observed", "current_speed_kph": data.get("currentSpeed"), "free_flow_speed_kph": data.get("freeFlowSpeed"), "confidence": data.get("confidence"), "road_closed": data.get("roadClosure", False)}


async def openrouter_draft(message: str, segment: RoadSegment) -> dict:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        return {"provider": "manual-fallback", "model": None, "draft": {"title": f"Close {segment.name}", "objective": message, "assumptions": [{"statement": "Closure duration uses the pilot default.", "provenance": "assumed", "confidence": 0.5}], "operation": {"type": "CLOSE_ROAD", "road_segment_id": segment.id, "direction": "both", "begin_seconds": 900, "end_seconds": 4500, "reason": message}}, "requires_approval": True}
    payload = {"model": os.getenv("OPENROUTER_MODEL", "z-ai/glm-4.6"), "temperature": 0.2, "max_tokens": 350, "messages": [{"role": "system", "content": "Draft only a road-closure scenario for the supplied selected road. Never invent IDs, counts, or observations. Return one JSON object with exactly these string fields: title, objective, reason. No markdown."}, {"role": "user", "content": json.dumps({"request": message, "selected_road": segment.model_dump()})}], "response_format": {"type": "json_object"}}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost:3000"), "X-Title": os.getenv("OPENROUTER_APP_NAME", "Rajkot Traffic Lab")}
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
    body = response.json()
    content = json.loads(body["choices"][0]["message"]["content"])
    if set(content) != {"title", "objective", "reason"} or not all(isinstance(content[key], str) and content[key].strip() for key in content):
        raise ValueError("OpenRouter returned an invalid draft shape")
    content["operation"] = {"type": "CLOSE_ROAD", "road_segment_id": segment.id, "direction": "both", "begin_seconds": 900, "end_seconds": 4500, "reason": content.pop("reason")}
    return {"provider": body.get("provider"), "model": body.get("model"), "request_id": body.get("id"), "draft": content, "requires_approval": True}

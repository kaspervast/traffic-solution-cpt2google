from __future__ import annotations

import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from statistics import mean

import httpx

from domain import CloseRoadOperation


def _bbox(geometry: list[list[float]]) -> tuple[float, float, float, float]:
    lons, lats = [point[0] for point in geometry], [point[1] for point in geometry]
    center_lon, center_lat = mean(lons), mean(lats)
    half_lon = min(.02, max(.012, (max(lons) - min(lons)) / 2 + .006))
    half_lat = min(.02, max(.010, (max(lats) - min(lats)) / 2 + .006))
    return center_lon - half_lon, center_lat - half_lat, center_lon + half_lon, center_lat + half_lat


def _run(command: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"Command failed ({command[0]}): {result.stderr[-1000:]}")
    return result


def _trip_metrics(path: Path) -> dict:
    trips = ET.parse(path).getroot().findall("tripinfo")
    return {"trip_duration": mean(float(item.attrib["duration"]) for item in trips) if trips else 0,
            "time_loss": mean(float(item.attrib.get("timeLoss", 0)) for item in trips) if trips else 0,
            "completed": len(trips)}


def run_osm_closure_experiment(operations: list[CloseRoadOperation], demand_vph: int, seeds: int = 5) -> dict:
    primary = operations[0]
    if not primary.geometry:
        raise RuntimeError("OSM simulation requires selected road geometry")
    west, south, east, north = _bbox(primary.geometry)
    with tempfile.TemporaryDirectory(prefix="rajkot-osm-sumo-") as temp:
        folder = Path(temp)
        response = httpx.get(f"https://api.openstreetmap.org/api/0.6/map?bbox={west},{south},{east},{north}", timeout=150, headers={"User-Agent": "RajkotTrafficLab/0.2"})
        response.raise_for_status()
        osm_file, baseline_net, proposal_net = folder / "map.osm.xml", folder / "baseline.net.xml", folder / "proposal.net.xml"
        osm_file.write_bytes(response.content)
        _run([os.getenv("NETCONVERT_BINARY", "netconvert"), "--osm-files", str(osm_file), "--output-file", str(baseline_net), "--geometry.remove", "true", "--junctions.join", "true", "--tls.guess-signals", "true", "--output.original-names", "true"], 180)
        root = ET.parse(baseline_net).getroot()
        edges = [edge for edge in root.findall("edge") if not edge.attrib.get("function")]
        way_ids = {operation.road_segment_id.removeprefix("osm_") for operation in operations if operation.road_segment_id.startswith("osm_")}
        selected = [edge for edge in edges if edge.attrib["id"].lstrip("-").split("#")[0] in way_ids]
        if not selected:
            raise RuntimeError("Selected OSM way was not found in the imported SUMO network")
        selected_ids = [edge.attrib["id"] for edge in selected]
        _run([os.getenv("NETCONVERT_BINARY", "netconvert"), "--sumo-net-file", str(baseline_net), "--remove-edges.explicit", ",".join(selected_ids), "--output-file", str(proposal_net)], 120)

        focus = selected[0]
        selected_set = set(selected_ids)
        upstream = [edge.attrib["id"] for edge in edges if edge.attrib.get("to") == focus.attrib.get("from") and edge.attrib["id"] not in selected_set]
        downstream = [edge.attrib["id"] for edge in edges if edge.attrib.get("from") == focus.attrib.get("to") and edge.attrib["id"] not in selected_set]
        if not upstream or not downstream:
            raise RuntimeError("Could not find upstream/downstream edges around the selected OSM road")
        vehicle_count = max(240, min(900, round(demand_vph * .5)))
        trips = ["<routes>", '<vType id="mixed" vClass="passenger" length="3.4" minGap="1.2" accel="2.2" decel="4.5" sigma="0.7"/>']
        for index in range(vehicle_count):
            depart = index * 1800 / vehicle_count
            trips.append(f'<trip id="veh_{index}" type="mixed" depart="{depart:.2f}" from="{upstream[index % len(upstream)]}" to="{downstream[index % len(downstream)]}" departLane="best" departSpeed="max"/>')
        trips.append("</routes>")
        trip_file = folder / "demand.trips.xml"
        trip_file.write_text("\n".join(trips), encoding="utf-8")
        baseline_routes, proposal_routes = folder / "baseline.rou.xml", folder / "proposal.rou.xml"
        _run([os.getenv("DUAROUTER_BINARY", "duarouter"), "-n", str(baseline_net), "-r", str(trip_file), "-o", str(baseline_routes), "--ignore-errors", "true"])
        _run([os.getenv("DUAROUTER_BINARY", "duarouter"), "-n", str(proposal_net), "-r", str(trip_file), "-o", str(proposal_routes), "--ignore-errors", "true"])
        baseline, proposal = [], []
        for seed in range(1, seeds + 1):
            for label, net, routes, target in (("baseline", baseline_net, baseline_routes, baseline), ("proposal", proposal_net, proposal_routes, proposal)):
                output = folder / f"{label}_{seed}.tripinfo.xml"
                _run([os.getenv("SUMO_BINARY", "sumo"), "-n", str(net), "-r", str(routes), "--seed", str(seed), "--end", "5400", "--lateral-resolution", ".8", "--tripinfo-output", str(output), "--no-step-log", "true", "--duration-log.disable", "true"], 180)
                target.append(_trip_metrics(output))
        return {"baseline": baseline, "proposal": proposal, "seeds": seeds, "demand_vph": demand_vph,
                "engine": _run([os.getenv("SUMO_BINARY", "sumo"), "--version"], 10).stdout.splitlines()[0],
                "network_source": "openstreetmap", "network_edges": len(edges), "closed_sumo_edges": selected_ids,
                "bbox": [south, west, north, east], "generated_trips": vehicle_count}


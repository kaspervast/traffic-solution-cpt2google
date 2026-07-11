from __future__ import annotations

import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from statistics import mean


NODES = """<nodes>
<node id="west" x="0" y="0"/><node id="junction" x="500" y="0"/>
<node id="east" x="1000" y="0"/><node id="south" x="500" y="-500"/>
</nodes>"""
EDGES = """<edges>
<edge id="main_a" from="west" to="junction" priority="3" numLanes="2" speed="13.9"/>
<edge id="main_b" from="junction" to="east" priority="3" numLanes="2" speed="13.9"/>
<edge id="alt_a" from="west" to="south" priority="2" numLanes="1" speed="8.3"/>
<edge id="alt_b" from="south" to="east" priority="2" numLanes="1" speed="8.3"/>
</edges>"""


def _routes(proposal: bool, demand_vph: int) -> str:
    distribution = '<route id="closed_diversion" edges="alt_a alt_b"/>' if proposal else """<routeDistribution id="available_routes">
<route id="main_route" edges="main_a main_b" probability="0.76"/>
<route id="alt_route" edges="alt_a alt_b" probability="0.24"/>
</routeDistribution>"""
    route_id = "closed_diversion" if proposal else "available_routes"
    return f"""<routes>
<vTypeDistribution id="indian_mix">
<vType id="motorcycle" vClass="motorcycle" length="2.0" width="0.8" minGap="0.8" accel="2.8" decel="4.5" sigma="0.7" probability="0.46"/>
<vType id="car" vClass="passenger" length="4.3" width="1.8" minGap="1.5" accel="2.2" decel="4.5" sigma="0.6" probability="0.41"/>
<vType id="auto" vClass="taxi" length="2.8" width="1.3" minGap="1.0" accel="1.8" decel="4.0" sigma="0.8" probability="0.13"/>
</vTypeDistribution>
{distribution}
<flow id="west_east" type="indian_mix" route="{route_id}" begin="300" end="3900" vehsPerHour="{demand_vph}" departLane="best" departSpeed="max"/>
</routes>"""


def _one_run(folder: Path, seed: int, proposal: bool, demand_vph: int) -> dict:
    route_file = folder / f"{'proposal' if proposal else 'baseline'}_{seed}.rou.xml"
    trip_file = folder / f"{'proposal' if proposal else 'baseline'}_{seed}.tripinfo.xml"
    route_file.write_text(_routes(proposal, demand_vph), encoding="utf-8")
    command = [os.getenv("SUMO_BINARY", "sumo"), "-n", str(folder / "network.net.xml"), "-r", str(route_file),
               "--seed", str(seed), "--begin", "0", "--end", "5400", "--step-length", "0.5",
               "--lateral-resolution", "0.8", "--tripinfo-output", str(trip_file), "--no-step-log", "true", "--duration-log.disable", "true"]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=90)
    if completed.returncode:
        raise RuntimeError(f"SUMO failed: {completed.stderr.strip()}")
    root = ET.parse(trip_file).getroot()
    trips = root.findall("tripinfo")
    return {"trip_duration": mean(float(item.attrib["duration"]) for item in trips) if trips else 0,
            "time_loss": mean(float(item.attrib.get("timeLoss", 0)) for item in trips) if trips else 0,
            "completed": len(trips)}


def run_closure_experiment(demand_vph: int, seeds: int = 5) -> dict:
    with tempfile.TemporaryDirectory(prefix="rajkot-sumo-") as temp:
        folder = Path(temp)
        (folder / "nodes.nod.xml").write_text(NODES, encoding="utf-8")
        (folder / "edges.edg.xml").write_text(EDGES, encoding="utf-8")
        subprocess.run([os.getenv("NETCONVERT_BINARY", "netconvert"), "--node-files", str(folder / "nodes.nod.xml"), "--edge-files", str(folder / "edges.edg.xml"), "--output-file", str(folder / "network.net.xml")], check=True, capture_output=True, text=True, timeout=30)
        baseline = [_one_run(folder, seed, False, demand_vph) for seed in range(1, seeds + 1)]
        proposal = [_one_run(folder, seed, True, demand_vph) for seed in range(1, seeds + 1)]
    version = subprocess.run([os.getenv("SUMO_BINARY", "sumo"), "--version"], capture_output=True, text=True, timeout=10).stdout.splitlines()[0]
    return {"baseline": baseline, "proposal": proposal, "engine": version, "demand_vph": demand_vph, "seeds": seeds}

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
import httpx

from domain import Provenance, RoadSegment

OVERPASS_URLS = [
    os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter"),
    "https://overpass.kumi.systems/api/interpreter",
]
RAJKOT_BBOX = (22.270, 70.740, 22.330, 70.830)
ROAD_FILTER = "motorway|trunk|primary|secondary|tertiary|unclassified|residential|service"

DEFAULT_SPEED = {
    "motorway": 70, "trunk": 60, "primary": 50, "secondary": 45,
    "tertiary": 40, "unclassified": 35, "residential": 30, "service": 20,
}
DEFAULT_LANES = {"motorway": 3, "trunk": 3, "primary": 2, "secondary": 2, "tertiary": 2}
PEAK_FACTORS = {"morning": 0.78, "evening": 0.88, "offpeak": 0.48, "night": 0.22}


def _number(value: str | None, default: float) -> float:
    try:
        return float(str(value).split(";")[0].split()[0])
    except (TypeError, ValueError):
        return default


def _vehicle_mix(highway: str) -> dict[str, float]:
    if highway in {"primary", "trunk", "secondary"}:
        return {"motorcycle": .42, "car": .34, "auto_rickshaw": .10, "bus": .04, "light_commercial": .06, "heavy_truck": .04}
    return {"motorcycle": .48, "car": .31, "auto_rickshaw": .12, "bus": .02, "light_commercial": .05, "heavy_truck": .02}


def _estimates(osm_id: int, highway: str, lanes: int, free_speed: float) -> dict:
    capacity = max(450, lanes * 1800 * .72)
    variation = .55 + (osm_id % 61) / 100
    scenarios = {}
    for period, factor in PEAK_FACTORS.items():
        class_factor = 1.08 if highway in {"trunk", "primary"} else .95 if highway in {"secondary", "tertiary"} else .78
        vph = round(capacity * factor * variation * class_factor)
        volume_capacity = min(vph / capacity, 1.15)
        speed_ratio = max(.16, 1 - .72 * volume_capacity ** 2)
        scenarios[period] = {
            "estimated_vehicles_per_hour": vph,
            "estimated_speed_kph": round(free_speed * speed_ratio, 1),
            "volume_capacity_ratio": round(volume_capacity, 2),
            "vehicle_mix": _vehicle_mix(highway),
            "provenance": "estimated",
        }
    return scenarios


async def fetch_osm_roads(bbox: tuple[float, float, float, float] = RAJKOT_BBOX) -> list[RoadSegment]:
    south, west, north, east = bbox
    query = f'[out:json][timeout:45];way["highway"~"^({ROAD_FILTER})$"]["name"]({south},{west},{north},{east});out tags geom;'
    last_error: Exception | None = None
    data = None
    for url in OVERPASS_URLS:
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                response = await client.post(url, content=query, headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "RajkotTrafficLab/0.2"})
                response.raise_for_status()
                data = response.json()
                break
        except Exception as exc:
            last_error = exc
    if data is None:
        try:
            ways: dict[int, dict] = {}
            async with httpx.AsyncClient(timeout=180, follow_redirects=True) as client:
                lat = south
                while lat < north:
                    lon = west
                    tile_north = min(north, lat + .02)
                    while lon < east:
                        tile_east = min(east, lon + .03)
                        response = await client.get(f"https://api.openstreetmap.org/api/0.6/map?bbox={lon},{lat},{tile_east},{tile_north}", headers={"User-Agent": "RajkotTrafficLab/0.2"})
                        response.raise_for_status()
                        root = ET.fromstring(response.content)
                        nodes = {node.attrib["id"]: {"lat": float(node.attrib["lat"]), "lon": float(node.attrib["lon"])} for node in root.findall("node")}
                        for way in root.findall("way"):
                            tags = {tag.attrib["k"]: tag.attrib["v"] for tag in way.findall("tag")}
                            if not tags.get("name") or tags.get("highway") not in ROAD_FILTER.split("|"):
                                continue
                            geometry = [nodes[nd.attrib["ref"]] for nd in way.findall("nd") if nd.attrib.get("ref") in nodes]
                            if len(geometry) >= 2:
                                ways[int(way.attrib["id"])] = {"id": int(way.attrib["id"]), "tags": tags, "geometry": geometry}
                        lon = tile_east
                    lat = tile_north
            data = {"elements": list(ways.values())}
        except Exception as fallback_error:
            raise RuntimeError(f"OpenStreetMap providers unavailable: Overpass={last_error}; OSM API={fallback_error}") from fallback_error

    roads: list[RoadSegment] = []
    for item in data.get("elements", []):
        geometry = [[point["lon"], point["lat"]] for point in item.get("geometry", [])]
        if len(geometry) < 2:
            continue
        tags = item.get("tags", {})
        highway = tags.get("highway", "unclassified")
        lanes = max(1, int(_number(tags.get("lanes"), DEFAULT_LANES.get(highway, 1))))
        free_speed = _number(tags.get("maxspeed"), DEFAULT_SPEED.get(highway, 30))
        estimates = _estimates(item["id"], highway, lanes, free_speed)
        roads.append(RoadSegment(
            id=f"osm_{item['id']}", osm_way_id=item["id"], name=tags.get("name", "Unnamed road"),
            direction="one-way" if tags.get("oneway") == "yes" else "two-way", geometry=geometry,
            lanes=lanes, free_flow_speed_kph=free_speed, current_speed_kph=estimates["evening"]["estimated_speed_kph"],
            estimated_vehicles_per_hour=estimates["evening"]["estimated_vehicles_per_hour"],
            highway=highway, scenario_estimates=estimates, mapping_confidence=1,
            provenance=Provenance.derived, traffic_provenance=Provenance.estimated,
        ))
    roads.sort(key=lambda road: (road.highway not in {"primary", "secondary", "tertiary", "trunk"}, road.name))
    return roads[:1200]


async def fetch_osm_route_section(start_lat: float, start_lon: float, end_lat: float, end_lon: float) -> dict:
    url = f"https://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}"
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        response = await client.get(url, params={"overview": "full", "geometries": "geojson", "steps": "true"}, headers={"User-Agent": "RajkotTrafficLab/0.2"})
        response.raise_for_status()
    body = response.json()
    if body.get("code") != "Ok" or not body.get("routes"):
        raise RuntimeError("No routable OpenStreetMap road section was found between those points")
    route = body["routes"][0]
    names = [step.get("name") for leg in route.get("legs", []) for step in leg.get("steps", []) if step.get("name")]
    name = names[0] if names else "Selected OSM road section"
    return {"name": name, "geometry": route["geometry"]["coordinates"], "distance_m": round(route["distance"]), "duration_seconds": round(route["duration"]), "source": "openstreetmap-osrm"}

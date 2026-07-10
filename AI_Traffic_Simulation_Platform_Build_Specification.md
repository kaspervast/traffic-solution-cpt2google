# AI-Assisted Traffic Simulation Platform

## Product Requirements, Architecture and Implementation Specification

**Primary simulation engine:** Eclipse SUMO  
**Map interface:** Google Maps JavaScript API  
**Traffic and incident intelligence:** TomTom Traffic API  
**Route observations:** Google Routes API  
**AI provider:** OpenRouter  
**AI model:** `z-ai/glm-4.6`  
**Initial target:** A small, real-world corridor or group of junctions in Rajkot, Gujarat  
**Document status:** Build-ready specification  
**Last reviewed:** 11 July 2026

---

## 1. Executive summary

Build a modern web application that hides SUMO's XML files, command-line tools and network identifiers behind a map-based interface. A user should be able to select an area, describe a traffic problem in plain language, review the AI's proposed changes, run a simulation and compare the results without knowing SUMO.

The platform must not allow the AI to alter simulation files directly. The AI converts natural-language requests into a validated, typed scenario plan. The user reviews the plan, the backend converts it into SUMO operations, and an isolated worker runs the simulation. Results are mapped back to understandable road names and displayed as a before-versus-after comparison.

Example user request:

> At 6:30 PM this road becomes very slow. It is narrow near the junction. Test what happens if heavy vehicles are restricted and the signal green time is increased for the main road.

Expected application response:

1. Identify the road and junction selected on the map.
2. Ask only for missing information that materially affects the scenario.
3. Show assumptions such as road capacity, time period and traffic increase.
4. Propose a restriction and signal-plan change.
5. Require user confirmation before running.
6. Run baseline and proposed scenarios using the same demand and random seed.
7. Display delay, speed, queue and spillover changes.
8. Explain whether the intervention helped, harmed or merely shifted congestion.

This is a decision-support and experimentation platform. It must never describe an AI estimate as measured traffic or recommend a real traffic-control change solely from an uncalibrated simulation.

---

## 2. Product goals

### 2.1 Primary goals

- Make SUMO usable by traffic officers, city engineers and analysts who do not know SUMO.
- Create a real road-network scenario from a selected area with minimal manual work.
- Support plain-language scenario creation through `z-ai/glm-4.6` on OpenRouter.
- Compare a baseline against one or more proposed interventions.
- Show where congestion improves and where it moves.
- Preserve data origin, timestamp, confidence and assumptions for every simulation.
- Produce an auditable report that another analyst can reproduce.
- Support Indian urban traffic characteristics, including cars, motorcycles, auto-rickshaws, buses and heavy vehicles.

### 2.2 Non-goals for the first release

- City-wide live traffic control.
- Automatically changing physical traffic signals.
- Replacing an engineering traffic study.
- Deriving exact vehicle counts from coloured traffic layers.
- Perfect lane-level reconstruction from Google or TomTom.
- Training a new foundation model.
- Simulating all of Rajkot in the first MVP.

### 2.3 Product principles

1. **Map first:** roads and junctions are selected visually.
2. **Progressive complexity:** default controls are simple; engineering controls are optional.
3. **AI proposes, user approves:** no hidden scenario changes.
4. **Provenance everywhere:** measured, provider-observed, estimated and assumed values are visibly different.
5. **Comparable experiments:** baseline and proposal use identical demand, seed and duration unless intentionally changed.
6. **Fail honestly:** missing data produces warnings, not fabricated precision.
7. **Reproducible:** every run stores input versions, configuration, seed and engine version.

---

## 3. Personas and permissions

### 3.1 Viewer

- Opens dashboards and completed simulations.
- Views maps, charts and reports.
- Cannot change scenarios or API configuration.

### 3.2 Traffic analyst

- Creates projects and scenarios.
- Imports road networks and traffic observations.
- Uses the AI assistant.
- Runs simulations and exports reports.
- Cannot manage users or production secrets.

### 3.3 Traffic engineer

- Has analyst permissions.
- Can edit lane mappings, junction connections, signal phases, saturation flows and calibration settings.
- Can approve a scenario as technically reviewed.

### 3.4 Administrator

- Manages users, organizations, quotas and API integrations.
- Configures retention policies and worker capacity.
- Can view provider usage and estimated cost.
- Cannot silently alter signed simulation reports.

### 3.5 Audit requirements

Record the user, timestamp, project, original value, changed value and reason for:

- Road or junction edits.
- Traffic-demand changes.
- AI-generated plans.
- User approvals and rejections.
- Calibration overrides.
- Simulation runs.
- Report approvals.

---

## 4. Core user experience

## 4.1 First-time onboarding

Use a five-step guided experience:

1. **Create project** — project name, city, timezone and purpose.
2. **Choose area** — search a place or draw a polygon on Google Maps.
3. **Build road network** — import an OSM network, validate it and show issues.
4. **Add traffic evidence** — TomTom snapshot, Google route probes, CSV counts or manual estimates.
5. **Run baseline** — create a first simulation and explain confidence limitations.

The user must see a progress indicator and be able to leave and return. Long-running jobs continue in the background.

### 4.2 Main workspace

Desktop layout:

- **Left rail:** Projects, Live Traffic, Scenarios, Runs, Reports and Settings.
- **Top bar:** Project selector, time window, data freshness, notifications and profile.
- **Centre:** Google map with selectable road, junction, incident and result layers.
- **Right inspector:** Details and editable controls for the selected object.
- **Bottom comparison drawer:** Baseline and proposal KPIs, timeline and charts.
- **AI assistant:** Collapsible panel on the right, never covering the selected map object.

Tablet layout:

- Map occupies the full canvas.
- Inspector and AI assistant open as bottom sheets.
- Comparison metrics use horizontally scrollable cards.

Mobile is view-oriented in the MVP. Editing a detailed signal phase plan should require tablet or desktop.

### 4.3 Primary workflow: create and test a scenario

1. Open a project.
2. Choose an existing baseline or create a baseline snapshot.
3. Click **New scenario**.
4. Select a road, junction or area.
5. Choose a quick action or describe the problem to the AI.
6. Review the AI's interpretation, assumptions and proposed operations.
7. Correct road selections or values if necessary.
8. Click **Validate scenario**.
9. Resolve blocking network or demand errors.
10. Click **Run comparison**.
11. Watch job stages: queued, preparing, routing, simulating, aggregating and complete.
12. Review before/after map layers and KPIs.
13. Ask the AI to explain the result.
14. Save, duplicate, export or submit for engineering review.

### 4.4 Quick actions

For a selected road:

- Close road.
- Close one direction.
- Reduce or add a lane.
- Set effective lane width.
- Change speed limit.
- Reduce effective capacity.
- Restrict a vehicle class.
- Add a bus stop or roadside obstruction.
- Increase or decrease incoming traffic.
- Set an incident duration.

For a selected junction:

- Add or remove a permitted turn.
- Add a traffic signal.
- Change phase duration.
- Use fixed-time or actuated control.
- Add a protected turn.
- Convert to priority junction or roundabout.
- Join incorrectly split junctions.

For a selected area:

- Apply demand multiplier.
- Add event traffic.
- Restrict heavy vehicles.
- Create origin/destination zones.
- Test an evacuation or diversion plan.

### 4.5 Plain-language examples

- “This section is narrow because vehicles park on the left. Reduce usable capacity by 35% from 5 PM to 9 PM.”
- “Close this bridge for 30 minutes and show the best diversion.”
- “Traffic coming from the west is much higher than the east. Test 20%, 40% and 60% increases.”
- “Create an actuated signal and compare it with the current 90-second fixed cycle.”
- “Why did the queue on the parallel road increase?”
- “Find the proposal with the lowest total delay without increasing any local road by more than 15%.”

---

## 5. UI and design system

### 5.1 Visual direction

Use a clean civic-technology aesthetic: trustworthy, restrained and data-rich without looking like an engineering tool from the 1990s.

- Font: Inter or Geist for UI; JetBrains Mono for identifiers and logs.
- Base colours: slate and neutral surfaces.
- Primary action: indigo or deep blue.
- Success: green.
- Warning: amber.
- Critical congestion: red.
- Simulation change: violet.
- Baseline: blue.
- Proposed: teal.
- Avoid using colour alone; include icons, labels and patterns.

### 5.2 Congestion legend

Use a consistent legend based on the speed-to-free-flow ratio:

| Ratio | Status | Suggested colour |
|---:|---|---|
| `>= 0.80` | Free | Green |
| `0.60–0.79` | Moderate | Yellow-green |
| `0.40–0.59` | Slow | Amber |
| `0.20–0.39` | Severe | Orange-red |
| `< 0.20` | Gridlock | Red |
| Unknown | No evidence | Grey, dashed |

Do not directly equate the Google categories `NORMAL`, `SLOW` and `TRAFFIC_JAM` with numeric vehicle counts.

### 5.3 Data provenance badges

Every important value must have one of these badges:

- **Measured:** survey, sensor or verified count.
- **Observed:** external provider observation.
- **Derived:** calculated from one or more observations.
- **Estimated:** model-generated estimate.
- **Assumed:** user or system default.
- **Simulated:** produced by SUMO.

Clicking the badge shows source, acquisition time, retention deadline, confidence and transformation history.

### 5.4 Accessibility

- Meet WCAG 2.2 AA where practical.
- Keyboard access for all controls.
- Visible focus states.
- Minimum 44 × 44 px touch targets.
- Charts include tabular alternatives.
- Map changes are announced in a status region.
- Respect reduced-motion preferences.
- Never use flashing animation for incidents.

### 5.5 Empty, loading and error states

Each page must explain:

- What the page is for.
- Why no content exists.
- The next useful action.
- Whether data is loading, stale, unavailable or forbidden.

Provider failure must not produce an empty green map. Show the provider, failure time, last successful observation and whether cached data is legally and technically usable.

---

## 6. High-level architecture

```mermaid
flowchart TD
    Web[Next.js web application] --> API[FastAPI application API]
    Web --> GMap[Google Maps JavaScript API]
    API --> AI[OpenRouter GLM-4.6]
    API --> Providers[Provider adapters]
    Providers --> GRoutes[Google Routes API]
    Providers --> TomTom[TomTom Traffic API]
    API --> DB[(PostgreSQL + PostGIS)]
    API --> Queue[Redis job queue]
    Queue --> Worker[Simulation worker]
    Worker --> SUMO[SUMO + libsumo/TraCI]
    Worker --> Store[Object storage]
    Worker --> DB
```

### 6.1 Recommended stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, TypeScript, React |
| UI | Tailwind CSS, shadcn/ui, Radix primitives |
| Map | Google Maps JavaScript API and Data layer |
| Forms | React Hook Form + Zod |
| Charts | Apache ECharts |
| Backend | Python 3.12+, FastAPI, Pydantic |
| Spatial database | PostgreSQL 16+ with PostGIS |
| Queue | Redis + Celery, Dramatiq or RQ |
| Simulation | SUMO, `sumo`, `netconvert`, `duarouter`, `libsumo`/TraCI |
| AI | OpenRouter Chat Completions API, `z-ai/glm-4.6` |
| Storage | S3-compatible object storage or MinIO |
| Authentication | Keycloak, Auth.js or managed OIDC |
| Observability | OpenTelemetry, Prometheus, Grafana, Sentry |
| Deployment | Docker Compose initially; Kubernetes only when required |

### 6.2 Service boundaries

Start as a modular monolith plus workers, not many microservices.

- `web`: browser user interface.
- `api`: authentication, projects, scenarios, validation and results.
- `worker-simulation`: network generation and SUMO execution.
- `worker-ingestion`: TomTom/Google acquisition and normalization.
- `postgres`: application and spatial data.
- `redis`: jobs, locks and short-lived cache.
- `object-store`: generated networks, route files, raw permitted artifacts and reports.

Split services only after load, ownership or security demands it.

### 6.3 Suggested repository structure

```text
traffic-platform/
├── apps/
│   ├── web/
│   └── api/
├── workers/
│   ├── ingestion/
│   └── simulation/
├── packages/
│   ├── contracts/
│   ├── design-system/
│   └── map-components/
├── simulation/
│   ├── network/
│   ├── demand/
│   ├── scenarios/
│   ├── metrics/
│   └── validation/
├── infrastructure/
│   ├── docker/
│   ├── migrations/
│   └── monitoring/
├── docs/
└── tests/
```

---

## 7. Road network strategy

### 7.1 Authoritative simulation topology

Use OpenStreetMap as the initial road-topology source for SUMO. Google Maps is the user-facing basemap and selection interface; Google map content must not be scraped to build the SUMO network.

Network pipeline:

1. User draws a polygon on Google Maps.
2. Backend stores the polygon as the project area of interest.
3. Ingestion worker downloads permitted OSM data for that polygon.
4. `netconvert` converts OSM data into a SUMO network.
5. Apply configured import rules for signals, junction joining, sidewalks and road classes.
6. Run topology validation.
7. Create simplified GeoJSON from SUMO edges for selection overlays.
8. Build a mapping between OSM way IDs, SUMO edges and display names.
9. Present detected issues for human review.

### 7.2 Required network validation

- Disconnected components.
- Unreachable directions.
- Missing or implausible lane counts.
- Missing speed limits.
- Split intersections that should be joined.
- Invalid turns or internal edges.
- Road geometry crossing without a junction.
- Duplicate parallel edges.
- Incorrect one-way direction.
- Traffic signals absent from known junctions.
- U-turns created accidentally.
- Very short edges likely to create unstable queues.

### 7.3 Map matching

Maintain an internal `road_segment` abstraction rather than exposing raw SUMO IDs. A road segment may map to one or more SUMO edges.

Matching inputs:

- Geometry proximity and direction.
- Road name.
- Functional road class.
- One-way direction.
- Start and end junction proximity.
- Provider-provided coordinates or geometry.

Each match stores:

- Candidate segments.
- Selected segment.
- Matching algorithm version.
- Confidence score.
- Whether a user verified it.

Low-confidence matches must be displayed for correction and excluded from automatic calibration.

---

## 8. Google Maps Platform integration

### 8.1 Intended use

Use Google Maps JavaScript API for:

- Visible basemap.
- Place and address search.
- Drawing the project boundary.
- Selecting map locations.
- Displaying internal network and simulation-result overlays.
- Optional Street View-assisted manual verification where licensed and appropriately attributed.

Use Google Routes API for limited, targeted route probes:

- Current and predicted travel duration between selected endpoints.
- Alternative-route comparison.
- Traffic-aware route geometry.
- Traffic categories along a returned polyline.
- India-specific experimental narrow-road or flyover information only when returned and explicitly marked experimental.

Google documents traffic intervals as `NORMAL`, `SLOW` or `TRAFFIC_JAM`; treat these as qualitative provider observations, not exact speeds or traffic counts. See [traffic-aware polylines](https://developers.google.com/maps/documentation/routes/traffic_on_polylines) and the [Routes API reference](https://developers.google.com/maps/documentation/routes/reference/rest/v2/TopLevel/computeRoutes).

### 8.2 Example route-probe request

```http
POST https://routes.googleapis.com/directions/v2:computeRoutes
Content-Type: application/json
X-Goog-Api-Key: ${GOOGLE_MAPS_SERVER_API_KEY}
X-Goog-FieldMask: routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline,routes.travelAdvisory.speedReadingIntervals
```

```json
{
  "origin": {
    "location": {
      "latLng": { "latitude": 22.3039, "longitude": 70.8022 }
    }
  },
  "destination": {
    "location": {
      "latLng": { "latitude": 22.2900, "longitude": 70.7800 }
    }
  },
  "travelMode": "DRIVE",
  "routingPreference": "TRAFFIC_AWARE_OPTIMAL",
  "extraComputations": ["TRAFFIC_ON_POLYLINE"],
  "polylineQuality": "HIGH_QUALITY"
}
```

Only request required fields. Route probes should be intentionally scheduled and cost-controlled, not blindly requested for every road every minute.

### 8.3 API key security

- Browser key: restrict by HTTPS referrer and only enable browser-required APIs.
- Server key: store in a secret manager, restrict by server egress IP when possible and enable only required APIs.
- Never return the server key to the browser.
- Use separate development, staging and production Google Cloud projects.
- Configure billing alerts and per-API quotas.
- Log request count and billing category, not secret headers.

### 8.4 Legal and licensing gate

This is a blocking production requirement, not an optional note.

As of this document's review date, Google's service-specific terms say Routes API content must not be used with a non-Google map and place limits on caching. See the current [Google Maps Platform Service Specific Terms](https://cloud.google.com/maps-platform/terms/maps-service-terms).

Before using Google-derived route or traffic content to calibrate SUMO, obtain a written licensing determination covering:

- Deriving simulation parameters from Routes API content.
- Retaining durations, traffic classifications and polylines.
- Combining Google observations with TomTom or OSM-derived datasets.
- Displaying provider data and simulated outputs in the same application.
- Required attribution.
- Retention and deletion schedules.

Until cleared, implement Google Routes as a user-facing, short-lived route comparison adapter. Do not permanently merge its content into the canonical road database or training dataset. Store only permitted operational metadata, and enforce deletion by policy.

---

## 9. TomTom Traffic API integration

### 9.1 Intended use

TomTom Traffic exposes traffic incidents and traffic flow. Its Flow Segment Data endpoint returns speed and travel-time information for the road fragment nearest supplied coordinates. Its incident endpoint returns incidents within or intersecting a bounding box. See the [TomTom Traffic API introduction](https://developer.tomtom.com/traffic-api/documentation/tomtom-maps/v1/product-information/introduction), [Flow Segment Data](https://developer.tomtom.com/traffic-api/documentation/tomtom-maps/v1/traffic-flow/flow-segment-data) and [Incident Details](https://developer.tomtom.com/traffic-api/documentation/tomtom-maps/v1/traffic-incidents/incident-details).

Use TomTom for:

- Current speed.
- Free-flow speed.
- Current and free-flow travel time.
- Confidence where provided.
- Road-closure indication.
- Incident type, severity, geometry and validity period.
- Visual traffic layer when licensed.

Do not assume a flow speed is a vehicle count. It can calibrate travel time and speed, while demand still requires counts, OD estimates or a separate calibration procedure.

### 9.2 Sampling strategy

Do not call Flow Segment Data for every map pixel. Create representative probe points:

- One per direction for important homogeneous road sections.
- Before and after major junctions.
- On bridge approaches and known bottlenecks.
- At corridor screen lines.
- Avoid points too close to competing parallel roads.

Adaptive schedule example:

| Period | Suggested cadence |
|---|---:|
| Morning peak | 2–5 minutes |
| Evening peak | 2–5 minutes |
| Normal daytime | 10–15 minutes |
| 2 PM–4 PM local low-demand period | 15–30 minutes |
| Night | 30–60 minutes |
| Active incident | 1–3 minutes for affected area only |

Actual cadence must comply with the contracted quota and licence.

### 9.3 Normalized observation

```json
{
  "provider": "tomtom",
  "provider_product": "flow_segment_data_v4",
  "observed_at": "2026-07-11T13:30:00+05:30",
  "requested_point": [70.8022, 22.3039],
  "matched_road_segment_id": "seg_01J...",
  "match_confidence": 0.93,
  "current_speed_kph": 21,
  "free_flow_speed_kph": 42,
  "current_travel_time_seconds": 118,
  "free_flow_travel_time_seconds": 59,
  "provider_confidence": 0.81,
  "road_closed": false,
  "provenance": "observed",
  "retention_expires_at": null
}
```

`retention_expires_at` must be populated if required by the applicable licence.

### 9.4 Incident handling

1. Query incidents for the active project bounding box.
2. Deduplicate by provider identifier and geometry/time overlap.
3. Map the incident to internal road segments.
4. Show unmatched incidents separately.
5. Allow the analyst to convert an incident into a scenario operation.
6. Do not automatically modify the approved baseline.
7. Expire incidents based on provider validity and refresh rules.

### 9.5 Provider separation

TomTom observations, Google observations, user counts and SUMO outputs must remain independently queryable. A fusion record may reference them, but it must never erase their provenance.

---

## 10. Demand modelling and calibration

### 10.1 Demand hierarchy

Use the best available evidence in this order:

1. Verified turning-movement counts.
2. Classified corridor counts.
3. Sensor, ANPR or CCTV-derived counts with quality checks.
4. Origin-destination survey or authorized aggregated probe data.
5. Calibrated demand inferred from several speed/travel-time observations.
6. Expert-entered estimates.
7. Synthetic random demand for demonstrations only.

### 10.2 Indian vehicle classes

Initial classes:

- Motorcycle/scooter.
- Car/SUV.
- Auto-rickshaw.
- Light commercial vehicle.
- Bus.
- Heavy truck.
- Emergency vehicle.
- Bicycle and pedestrian where the study requires them.

For each class configure length, width, acceleration, deceleration, maximum speed, minimum gap, imperfection and passenger-car equivalent. Defaults must be labelled assumed until calibrated locally.

### 10.3 Baseline calibration

Calibration target metrics:

- Link travel times.
- Speed by road section and time window.
- Queue lengths at selected junction approaches.
- Turning counts.
- Completed flow through screen lines.
- Route choice proportions where available.

Suggested objective:

```text
score =
    w1 * normalized_travel_time_error
  + w2 * normalized_flow_error
  + w3 * normalized_queue_error
  + w4 * route_share_error
```

Use an optimizer only after the basic network is manually checked. Constrain parameters to plausible ranges. An optimizer can otherwise compensate for a broken junction by inventing unrealistic demand.

### 10.4 Confidence grade

| Grade | Meaning |
|---|---|
| A | Calibrated with recent classified counts and travel times |
| B | Calibrated with partial counts and several observed travel times |
| C | Calibrated mainly from speed/travel-time observations |
| D | Expert assumptions with limited observation |
| E | Synthetic demonstration; not suitable for decisions |

Every result screen and report must display the baseline confidence grade.

---

## 11. SUMO integration

### 11.1 Execution model

- Use command-line SUMO for batch runs.
- Use `libsumo` where high-throughput in-process execution is appropriate.
- Use TraCI for interactive stepping or dynamic controls.
- Never expose SUMO directly to the public network.
- Run each job in an isolated working directory or container.
- Apply CPU, memory, runtime and output-size limits.

### 11.2 Scenario operation contract

The application operates on domain-level commands:

```json
{
  "scenario_id": "scn_01J...",
  "baseline_id": "base_01J...",
  "operations": [
    {
      "type": "SET_EFFECTIVE_CAPACITY",
      "road_segment_id": "seg_01J...",
      "capacity_multiplier": 0.65,
      "begin_seconds": 0,
      "end_seconds": 7200,
      "reason": "Roadside parking reduces usable width"
    },
    {
      "type": "RESTRICT_VEHICLE_CLASS",
      "road_segment_id": "seg_01J...",
      "vehicle_class": "heavy_truck",
      "begin_seconds": 0,
      "end_seconds": 7200
    }
  ]
}
```

The compiler converts this contract into SUMO network, route, additional or TraCI operations. Store the compiled artifacts alongside the original contract.

### 11.3 Supported operation types

- `CLOSE_ROAD`
- `CLOSE_LANE`
- `SET_LANE_COUNT`
- `SET_EFFECTIVE_CAPACITY`
- `SET_SPEED_LIMIT`
- `SET_LANE_WIDTH`
- `RESTRICT_VEHICLE_CLASS`
- `SET_DEMAND_MULTIPLIER`
- `ADD_FLOW`
- `ADD_INCIDENT`
- `ADD_PARKING_OBSTRUCTION`
- `SET_TURN_PERMISSION`
- `ADD_TRAFFIC_SIGNAL`
- `SET_SIGNAL_PROGRAM`
- `SET_SIGNAL_PHASE_DURATION`
- `SET_SIGNAL_CONTROL_TYPE`
- `ADD_DIVERSION`
- `ADD_BUS_STOP`
- `ADD_OVERPASS_CONNECTION`
- `ADD_UNDERPASS_CONNECTION`

Overpass and underpass operations require topology changes and engineering review. They cannot be treated as a simple visual line drawn over the map.

### 11.4 Validation before execution

Blocking errors:

- Unknown or ambiguous road mapping.
- Invalid time range.
- Lane count below one unless the road is closed.
- Route references an unreachable destination.
- Signal program contains unsafe conflicting green movements.
- Scenario disconnects required OD pairs without an explicit closure objective.
- Missing network or demand version.
- AI operation is outside the allowed schema.

Warnings:

- Traffic evidence is stale.
- Capacity is assumed.
- Demand exceeds insertion capacity.
- Simulation warm-up is too short.
- Selected area is too small and boundary queues dominate results.
- A change causes high teleport or collision counts.

### 11.5 Run configuration

Each comparison run records:

- SUMO version.
- Network version and checksum.
- Demand version and checksum.
- Scenario contract version.
- Simulation start, end and warm-up.
- Step length.
- Random seed.
- Routing mode.
- Vehicle-class parameters.
- Signal programs.
- Output configuration.
- Worker image digest.

Use at least 5–10 random seeds for decision-quality comparisons when demand is stochastic. Present the mean and uncertainty, not only the best run.

### 11.6 Output metrics

Network level:

- Mean and percentile trip duration.
- Mean and percentile time loss.
- Total waiting time.
- Completed and unfinished trips.
- Depart delay and insertion backlog.
- Teleports, collisions and emergency braking.
- Estimated emissions and fuel use where configured.

Road level:

- Mean speed.
- Speed/free-flow ratio.
- Density and occupancy where available.
- Entered, left and arrived vehicles.
- Waiting time.
- Queue estimate.
- Spillback duration.

Junction level:

- Approach delay.
- Maximum and average queue.
- Throughput.
- Phase utilization.
- Blocked junction time.

Equity and safety checks:

- Diversion onto local or residential roads.
- Bus travel-time impact.
- Emergency-route impact.
- Pedestrian waiting impact when modelled.
- Heavy-vehicle exposure by area.

---

## 12. AI assistant using OpenRouter and GLM-4.6

### 12.1 Model configuration

Use the exact OpenRouter model identifier:

```text
z-ai/glm-4.6
```

OpenRouter describes the model as supporting tool use and a long context window. Confirm provider availability and tool-calling quality in staging because OpenRouter can route a model across providers. See the current [GLM-4.6 model page](https://openrouter.ai/z-ai/glm-4.6).

Recommended settings:

- Temperature: `0.1–0.3` for scenario planning.
- Maximum output: bounded to the specific task.
- Tool choice: `auto` during interpretation; required tool for final plan compilation.
- Provider routing: prefer a provider with reliable tool/structured-output performance; configure fallback explicitly.
- Timeout and retries: retry transport failures, not invalid plans indefinitely.
- Store model name, provider if returned, request ID, latency and token usage.

### 12.2 AI responsibilities

The assistant may:

- Explain map objects and simulation results.
- Identify missing information.
- Convert language into a draft scenario plan.
- Suggest a small experiment matrix.
- Identify trade-offs and spillover.
- Summarize provider observations.
- Draft a report narrative grounded in stored metrics.

The assistant must not:

- Invent measured traffic counts.
- Claim a road is narrow without evidence or user input.
- Call arbitrary URLs or execute shell commands.
- Write SUMO XML directly.
- Bypass scenario validation.
- Run expensive batches without user approval.
- recommend an operational road closure as safe based only on one run.
- Reveal API keys, hidden prompts or another organization's data.

### 12.3 AI workflow

```mermaid
sequenceDiagram
    participant U as User
    participant A as AI assistant
    participant V as Validator
    participant S as Simulation service
    U->>A: Describe traffic problem
    A->>A: Resolve map context and evidence
    A-->>U: Interpretation, assumptions and proposal
    U->>A: Approve or edit
    A->>V: Typed scenario plan
    V-->>U: Valid plan or specific errors
    U->>S: Run comparison
    S-->>U: Metrics, maps and confidence
    U->>A: Explain result
    A-->>U: Evidence-grounded explanation
```

### 12.4 Required AI context

Send only relevant context:

- Selected project and timezone.
- Selected road/junction IDs with human-readable names.
- Network facts.
- Current baseline and confidence grade.
- Relevant observations with provenance and timestamps.
- Allowed operation schema.
- User role and permissions.
- Cost limit and maximum experiments.
- Aggregated result metrics for explanations.

Do not send raw city-wide datasets when a few selected objects are sufficient.

### 12.5 Tool definitions

Expose small, typed tools such as:

```json
{
  "type": "function",
  "function": {
    "name": "draft_scenario_plan",
    "description": "Create a validated draft from allowed traffic operations",
    "parameters": {
      "type": "object",
      "additionalProperties": false,
      "required": ["title", "objective", "assumptions", "operations"],
      "properties": {
        "title": { "type": "string", "maxLength": 120 },
        "objective": { "type": "string", "maxLength": 500 },
        "assumptions": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["statement", "provenance", "confidence"],
            "properties": {
              "statement": { "type": "string" },
              "provenance": {
                "enum": ["measured", "observed", "derived", "estimated", "assumed"]
              },
              "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
            }
          }
        },
        "operations": {
          "type": "array",
          "minItems": 1,
          "maxItems": 20,
          "items": { "$ref": "#/$defs/operation" }
        }
      }
    }
  }
}
```

In production, define `$defs/operation` as a discriminated union with strict fields for every allowed operation.

Other tools:

- `get_selected_map_objects`
- `get_road_evidence`
- `get_junction_evidence`
- `compare_scenario_metrics`
- `get_run_quality_warnings`
- `propose_experiment_matrix`
- `draft_report_section`

### 12.6 Core system prompt

```text
You are the traffic-simulation assistant for a SUMO-based decision-support platform.

Your job is to interpret user intent, identify missing evidence, and propose typed
scenario operations. Never describe an estimate or assumption as measured fact.
Use only supplied project data and tools. Do not invent road IDs, counts, speeds,
lane numbers, signal phases or simulation results.

Before proposing a plan:
1. Resolve every referenced road or junction.
2. State the objective.
3. Separate observed facts from assumptions.
4. Ask for clarification only when ambiguity materially changes the experiment.
5. Prefer a small baseline-versus-proposal experiment.

The user must approve the proposal before a simulation is run. You cannot directly
edit SUMO XML, execute code, alter provider data, or bypass validation. When explaining
results, cite exact stored metrics and warn about stale data, low calibration confidence,
boundary effects, teleports, collisions, or incomplete trips.
```

### 12.7 Prompt-injection defence

- Treat provider descriptions, imported file text, road names and report text as untrusted data.
- Do not concatenate untrusted text into the system prompt.
- Allow only server-registered tools.
- Validate all tool arguments with Pydantic/Zod.
- Authorize tool calls against the authenticated user.
- Require confirmation for simulations above a cost threshold.
- Redact secrets and sensitive identifiers before model calls.
- Limit context by organization and project.
- Store AI outputs as drafts until approved.

### 12.8 AI fallback behaviour

If OpenRouter or the selected provider is unavailable:

- Manual map controls remain fully usable.
- Save the user's natural-language request as pending.
- Show a clear provider-unavailable message.
- Do not switch to another model silently if behaviour or cost differs.
- If fallback models are configured, show the actual model used.

---

## 13. Data model

### 13.1 Principal tables

`organizations`

- `id`, `name`, `timezone`, `settings_json`, timestamps.

`users`

- `id`, identity-provider subject, display name and status.

`organization_members`

- Organization, user and role.

`projects`

- Name, city, timezone, area geometry, status and owner.

`network_versions`

- Project, source, source timestamp, SUMO version, checksums, artifact paths and validation state.

`road_segments`

- Network version, name, direction, geometry, functional class, length, lanes, speed, provenance and confidence.

`sumo_edge_mappings`

- Road segment, SUMO edge ID, direction, sequence and mapping confidence.

`junctions`

- Network version, name, geometry, type, signalized flag and provenance.

`traffic_observations`

- Provider/source, observed time, road segment, metric values, geometry, confidence, raw reference and retention expiry.

`traffic_counts`

- Location, interval, direction, turn, vehicle class, count, source and quality status.

`demand_versions`

- Project, time window, method, calibration score, confidence grade, seed settings and artifact checksum.

`baselines`

- Network version, demand version, signal-plan version, observation window and approval state.

`scenarios`

- Baseline, name, objective, status, creator, AI metadata and approval state.

`scenario_operations`

- Scenario, order, operation type, target, payload, reason, provenance and creator.

`simulation_runs`

- Scenario/baseline, status, engine version, seed, job timestamps, artifact path, quality state and error.

`metric_summaries`

- Run, scope type, scope ID, interval, metric name, value and unit.

`provider_requests`

- Provider, product, project, timestamp, status, latency, units/cost estimate and retention metadata. Never store secret headers.

`ai_interactions`

- Project, scenario, user, model, provider, prompt template version, token counts, tool calls, approval and redacted content reference.

`audit_events`

- Actor, action, entity, before/after JSON, timestamp, IP metadata and correlation ID.

### 13.2 Spatial indexes

Use GiST indexes for project area, road geometry, junction geometry, observation geometry and incident geometry. Use time-partitioning for high-volume observations and metric samples.

### 13.3 Retention

Retention is provider- and contract-specific. Implement deletion as data, not as a manual promise:

- `retention_policy_id`
- `retention_expires_at`
- `deletion_status`
- `legal_hold`
- `derived_from_restricted_source`

A scheduled job deletes or anonymizes expired content and records the action.

---

## 14. Application API

### 14.1 Project and network

```text
POST   /api/v1/projects
GET    /api/v1/projects/{projectId}
PATCH  /api/v1/projects/{projectId}
POST   /api/v1/projects/{projectId}/network-imports
GET    /api/v1/network-imports/{jobId}
GET    /api/v1/network-versions/{networkVersionId}/segments
GET    /api/v1/network-versions/{networkVersionId}/issues
POST   /api/v1/network-versions/{networkVersionId}/approve
```

### 14.2 Observations

```text
POST   /api/v1/projects/{projectId}/observations/tomtom/snapshot
POST   /api/v1/projects/{projectId}/observations/google/route-probe
POST   /api/v1/projects/{projectId}/counts/import
GET    /api/v1/projects/{projectId}/observations
GET    /api/v1/road-segments/{segmentId}/evidence
```

### 14.3 Scenarios and runs

```text
POST   /api/v1/projects/{projectId}/scenarios
GET    /api/v1/scenarios/{scenarioId}
POST   /api/v1/scenarios/{scenarioId}/operations
POST   /api/v1/scenarios/{scenarioId}/validate
POST   /api/v1/scenarios/{scenarioId}/approve
POST   /api/v1/scenarios/{scenarioId}/runs
GET    /api/v1/runs/{runId}
GET    /api/v1/runs/{runId}/metrics
GET    /api/v1/runs/{runId}/map-layer
POST   /api/v1/runs/compare
```

### 14.4 AI

```text
POST   /api/v1/assistant/conversations
POST   /api/v1/assistant/conversations/{conversationId}/messages
POST   /api/v1/assistant/plans/{planId}/approve
POST   /api/v1/assistant/plans/{planId}/reject
GET    /api/v1/assistant/plans/{planId}
```

Use server-sent events or WebSockets for AI streaming and job progress. Job state in the database remains authoritative.

### 14.5 API response conventions

- UTC timestamps in storage; render in project timezone.
- Distances stored in metres and speeds in metres/second internally.
- Display km/h and local units.
- Stable error codes plus human-readable messages.
- Correlation ID on every request.
- Idempotency key for create-run and provider-snapshot calls.
- Cursor pagination for large spatial results.

---

## 15. Results and decision-support experience

### 15.1 Comparison header

Show:

- Baseline name and version.
- Proposal name and version.
- Simulation time window.
- Number of seeds.
- Calibration grade.
- Data freshness.
- Quality warnings.

### 15.2 KPI cards

Each card contains baseline, proposal, absolute change, percentage change and whether lower or higher is desirable.

Required cards:

- Average trip time.
- Average delay/time loss.
- Total waiting time.
- Completed trips.
- Worst queue.
- Network mean speed.
- Teleports/collisions.
- Emergency route time where configured.

Do not show a green “improvement” if completed trips decreased materially or simulation quality failed.

### 15.3 Map modes

- Baseline.
- Proposal.
- Difference.
- Side-by-side synchronized maps.
- Swipe comparison.
- Queue hotspots.
- Rerouted traffic.
- Incident and intervention layer.
- Evidence/confidence layer.

Clicking a road opens a mini comparison chart and the exact evidence used.

### 15.4 AI explanation format

The assistant should answer in this order:

1. Direct conclusion.
2. Main metric changes.
3. Where traffic improved.
4. Where congestion shifted or worsened.
5. Quality and confidence limitations.
6. Next experiment, if useful.

Example:

> The proposal reduced network-wide average delay by 11%, but it shifted traffic onto two local roads. Segment A improved from 18 km/h to 27 km/h, while Segment B's delay increased by 19%. Because this baseline has confidence grade C and no turning count exists for the western approach, treat the result as directional rather than final.

### 15.5 Reports

Generate HTML and PDF reports containing:

- Executive summary.
- Study area and time window.
- Data sources and freshness.
- Assumptions and exclusions.
- Network and demand versions.
- Scenario operations.
- Baseline-versus-proposal metrics.
- Maps and charts.
- Spillover and safety checks.
- Simulation quality warnings.
- AI-generated narrative clearly labelled as such.
- Reproducibility appendix.
- Approval and audit history.

---

## 16. Cost and quota controls

### 16.1 Google and TomTom

- Define a project-level sampling budget.
- Use adaptive sampling by time and incident state.
- Deduplicate identical route probes.
- Cache only where licence and product terms permit.
- Use field masks for Google Routes.
- Stop acquisition when the project is archived.
- Provide an administrator cost dashboard.
- Alert at 50%, 75%, 90% and 100% of quota.

### 16.2 OpenRouter

- Set per-user daily token and monetary limits.
- Summarize old conversation context instead of resending it indefinitely.
- Send selected map context, not entire projects.
- Cache static system instructions within supported provider rules.
- Show an estimate before large experiment-generation requests.
- Record the actual model and provider used.

### 16.3 SUMO workers

- Estimate run complexity from edge count, vehicle count, duration and seeds.
- Set role-based maximums.
- Cancel jobs that exceed hard resource limits.
- Allow a fast preview run and a slower decision-quality run.
- Reuse immutable baseline artifacts.

---

## 17. Security and privacy

### 17.1 Security baseline

- OIDC authentication with MFA for administrators.
- Organization and project-level authorization.
- TLS everywhere.
- Encrypted database and object storage.
- Secrets in a secret manager.
- Dependency and container scanning.
- Rate limiting and abuse protection.
- CSRF protection where cookie sessions are used.
- Content Security Policy configured for Google Maps and required endpoints.
- Signed, short-lived artifact URLs.
- Immutable audit events for sensitive actions.

### 17.2 Data minimization

The platform should normally store aggregated traffic observations, not personal movement histories. If CCTV, ANPR or device-level data is ever introduced, create a separate privacy and legal design before implementation.

### 17.3 Simulation isolation

- Never pass user-controlled strings into a shell command.
- Use fixed executable paths and argument arrays.
- Validate XML generation.
- Run workers without root.
- Mount scenario directories with the minimum access needed.
- Disable unnecessary network access inside simulation containers.
- Limit decompressed upload size and reject archive traversal.

---

## 18. Reliability and observability

### 18.1 Health indicators

- API availability and latency.
- Database and queue health.
- Worker capacity.
- Provider success/error rate.
- Data freshness by project.
- AI invalid-tool-call rate.
- Simulation failure and timeout rate.
- Report-generation failures.

### 18.2 Structured logging

Include:

- Correlation ID.
- Organization/project identifiers.
- Job or run ID.
- Provider/product without secrets.
- Duration and result status.
- SUMO exit code and categorized warning counts.

Do not log API keys, authorization headers, unredacted AI prompts containing sensitive data or raw uploaded personal data.

### 18.3 Recovery

- Jobs are idempotent or safely resumable.
- Workers write to temporary artifacts and atomically finalize.
- Stuck jobs are detected and marked.
- Database backups are tested.
- Object-storage versions and lifecycle policies are configured.
- A run can be recreated from its immutable inputs.

---

## 19. Testing strategy

### 19.1 Unit tests

- Domain operation validation.
- Unit conversion.
- Provider response normalization.
- Map matching.
- Metric aggregation.
- Retention calculation.
- Authorization.
- AI tool-argument validation.

### 19.2 Contract tests

- Google Routes request/response fixtures.
- TomTom Flow and Incident fixtures.
- OpenRouter tool-call fixtures.
- SUMO version compatibility.
- Frontend/backend generated contracts.

Use recorded or synthetic fixtures in continuous integration; do not incur live API cost for every test.

### 19.3 Simulation golden tests

Create small known networks:

- Straight road with known flow.
- Signalized four-way junction.
- Road closure with one alternative.
- Bottleneck lane reduction.
- Overpass geometry without an at-grade connection.
- Incident with dynamic rerouting.

Assert expected directional behaviour and acceptable metric ranges rather than fragile exact values.

### 19.4 AI evaluation

Maintain a test set containing:

- Clear requests.
- Ambiguous road references.
- Missing traffic counts.
- Conflicting instructions.
- Prompt-injection attempts in imported text.
- Requests exceeding user permissions.
- Requests for unsupported physical changes.
- Result explanations with hidden quality failures.

Measure:

- Correct target resolution.
- Unsupported-claim rate.
- Valid tool-call rate.
- Assumption disclosure.
- Appropriate clarification.
- Grounded metric citations.

### 19.5 User acceptance tests

A beginner should be able to:

- Create a small project without opening a terminal.
- Select and close a road.
- Increase traffic by 25%.
- Change a signal phase.
- Run a comparison.
- Identify whether congestion shifted.
- Export a report.

---

## 20. Implementation phases

### Phase 0 — Feasibility and licensing, 1–2 weeks

- Confirm Google, TomTom and OSM licensing for the intended data combination and retention.
- Verify TomTom coverage and useful flow results for target Rajkot roads.
- Verify Google route and narrow-road/flyover responses in the target area.
- Test `z-ai/glm-4.6` tool calls through OpenRouter.
- Select one corridor with available ground-truth observations.

**Exit:** written data-use decision, working API proofs and selected pilot area.

### Phase 1 — Foundation, 2–3 weeks

- Create monorepo and Docker development environment.
- Add authentication and organizations/projects.
- Add PostGIS migrations.
- Build Google map workspace and polygon selection.
- Implement background jobs and progress updates.
- Add secret and configuration management.

**Exit:** user can create a project, select an area and see a persistent map workspace.

### Phase 2 — Network builder, 3–4 weeks

- Import OSM for project area.
- Convert to SUMO using `netconvert`.
- Store network version and artifacts.
- Generate selectable road/junction overlays.
- Add network validation and issue-review UI.
- Add internal road-to-SUMO mapping.

**Exit:** approved SUMO network can be opened and inspected entirely through the web UI.

### Phase 3 — Baseline and manual scenarios, 4–5 weeks

- Implement synthetic/manual demand.
- Configure Indian vehicle classes.
- Add road closure, lane/capacity, speed, demand and signal operations.
- Build scenario validator and compiler.
- Run baseline/proposal jobs.
- Aggregate basic metrics.
- Build comparison cards and map difference layer.

**Exit:** manual baseline-versus-proposal workflow works end to end.

### Phase 4 — Provider observations, 3–4 weeks

- Implement TomTom flow probes and incident snapshots.
- Implement targeted Google route probes.
- Add provenance, freshness and retention.
- Build evidence inspector.
- Add CSV traffic-count import.
- Add initial demand calibration.

**Exit:** baseline can be supported by traceable real observations and receives a confidence grade.

### Phase 5 — AI assistant, 3–4 weeks

- Integrate OpenRouter.
- Add strict tool schemas.
- Implement selected-object context.
- Add draft/approve/reject scenario workflow.
- Add grounded result explanations.
- Add AI security and evaluation suite.

**Exit:** AI can reliably draft supported scenarios without directly editing SUMO or inventing data.

### Phase 6 — Reports and hardening, 3–4 weeks

- Add PDF/HTML reporting.
- Add multi-seed uncertainty.
- Add audit and approval workflows.
- Add quotas, monitoring and failure recovery.
- Perform security, load and accessibility testing.
- Conduct pilot user testing.

**Exit:** pilot-ready system for a limited real study.

---

## 21. MVP acceptance criteria

The MVP is complete only when:

- A user can draw a study area on Google Maps.
- The backend can build a valid SUMO network from permitted OSM data.
- Roads and junctions can be selected by human-readable names.
- The user can create road-closure, capacity, demand and signal-timing scenarios.
- Scenario operations are validated before compilation.
- Baseline and proposal use matching inputs and seed.
- TomTom flow/incident and Google route probes work through isolated adapters.
- Every observation displays source, timestamp and confidence/provenance.
- `z-ai/glm-4.6` creates a typed draft plan and cannot bypass user approval.
- Results show delay, speed, waiting, throughput, worst queue and spillover.
- Quality failures prevent misleading green success indicators.
- A report contains versions, assumptions, warnings and reproducibility data.
- Secrets never appear in frontend bundles or logs.
- Provider quotas and retention rules are enforced.

---

## 22. Initial pilot recommendation

Choose one corridor containing 3–5 connected junctions, not the whole city. The pilot should include:

- One known congested junction.
- At least one alternative route.
- A bridge, narrow section or lane bottleneck if relevant.
- Manual counts for at least one peak hour.
- Travel-time observations for both directions.
- Existing signal timings or a verified statement that the junction is unsignalized.

Run these first experiments:

1. Baseline validation.
2. 25% and 50% demand increase.
3. One-lane closure or roadside obstruction.
4. Complete road closure and diversion.
5. Fixed signal timing adjustment.
6. Actuated signal comparison.
7. Heavy-vehicle restriction.

Do not proceed to a city-wide simulation until the baseline reproduces observed corridor travel times and queues with acceptable error.

---

## 23. Environment variables

```dotenv
APP_ENV=development
APP_BASE_URL=http://localhost:3000
API_BASE_URL=http://localhost:8000

DATABASE_URL=postgresql+psycopg://traffic:change-me@postgres:5432/traffic
REDIS_URL=redis://redis:6379/0
OBJECT_STORAGE_ENDPOINT=http://minio:9000
OBJECT_STORAGE_BUCKET=traffic-artifacts

GOOGLE_MAPS_BROWSER_API_KEY=
GOOGLE_MAPS_SERVER_API_KEY=
TOMTOM_API_KEY=

OPENROUTER_API_KEY=
OPENROUTER_MODEL=z-ai/glm-4.6
OPENROUTER_SITE_URL=https://your-domain.example
OPENROUTER_APP_NAME=AI Traffic Simulation Platform

SUMO_HOME=/usr/share/sumo
SUMO_BINARY=/usr/bin/sumo
NETCONVERT_BINARY=/usr/bin/netconvert
DUAROUTER_BINARY=/usr/bin/duarouter

OIDC_ISSUER=
OIDC_CLIENT_ID=
OIDC_CLIENT_SECRET=
```

Provide `.env.example` with blank values. Never commit a populated `.env` file.

---

## 24. Definition of done for every feature

A feature is done when:

- Product flow and edge cases are documented.
- Authorization is implemented.
- Input and output schemas are strict.
- Loading, empty, stale and failure states exist.
- Provenance is preserved.
- Audit events are recorded where required.
- Unit and integration tests pass.
- Accessibility is reviewed.
- Metrics and logs are added.
- Secrets and personal data are not leaked.
- Documentation is updated.
- A beginner can complete the intended action without terminal access.

---

## 25. Reference links

- [Eclipse SUMO documentation](https://eclipse.dev/sumo/docs/)
- [SUMO beginner tutorial and osmWebWizard](https://eclipse.dev/sumo/docs/Tutorials/2022.html)
- [Google Routes API](https://developers.google.com/maps/documentation/routes)
- [Google traffic-aware polylines](https://developers.google.com/maps/documentation/routes/traffic_on_polylines)
- [Google Routes API REST reference](https://developers.google.com/maps/documentation/routes/reference/rest/v2/TopLevel/computeRoutes)
- [Google Maps Platform Service Specific Terms](https://cloud.google.com/maps-platform/terms/maps-service-terms)
- [TomTom Traffic API introduction](https://developer.tomtom.com/traffic-api/documentation/tomtom-maps/v1/product-information/introduction)
- [TomTom Flow Segment Data](https://developer.tomtom.com/traffic-api/documentation/tomtom-maps/v1/traffic-flow/flow-segment-data)
- [TomTom Incident Details](https://developer.tomtom.com/traffic-api/documentation/tomtom-maps/v1/traffic-incidents/incident-details)
- [OpenRouter GLM-4.6](https://openrouter.ai/z-ai/glm-4.6)

---

## Final implementation instruction

Build the platform in vertical slices. The first vertical slice must take one small mapped area through network import, manual demand, one scenario operation, SUMO execution and a comparison result. Do not start by building a large AI chat interface or a city-wide ingestion system. The AI becomes useful only after the underlying map objects, scenario operations and result metrics are trustworthy.

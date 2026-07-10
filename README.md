# Rajkot Traffic Lab

An auditable vertical slice for selecting a Rajkot corridor, importing traffic evidence, drafting a road closure, and comparing matched SUMO-style baseline/proposal runs.

## Quick start without Docker

Requirements: Node 22+, Python 3.11+, and SUMO 1.27+.

```powershell
Copy-Item .env.example .env
python -m venv .venv
.venv\Scripts\pip install -r apps/api/requirements.txt
npm install
```

Run the API and web app in separate terminals:

```powershell
.venv\Scripts\uvicorn main:app --app-dir apps/api --reload --port 8000
npm run dev
```

Open http://localhost:3000. With no Google browser key the workspace uses the accessible schematic corridor map. Live provider buttons remain disabled until keys are added to `.env`.

## Docker

Install Docker Desktop, copy `.env.example` to `.env`, and run:

```powershell
docker compose up --build
```

The compose stack includes web, API, worker, PostgreSQL/PostGIS, Redis, and MinIO. The API currently keeps pilot workflow state in memory so the vertical slice remains immediately runnable; the SQL migration defines the durable production schema.

## Evidence templates

- `examples/traffic_counts.csv`
- `examples/travel_times.csv`

All observed values retain source and timestamp. Simulation conclusions are directional until calibration passes the GEH and travel-time gates.

## Security

Never commit `.env`. Browser, TomTom, and OpenRouter keys must be restricted at their providers. Any keys previously pasted into chat should be revoked and replaced before use.


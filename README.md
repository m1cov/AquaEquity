# AquaField

Smart irrigation dashboard for North Macedonia. React frontend + FastAPI backend
with an Extended Kalman Filter for daily soil-water estimation, Sentinel-2 NDVI
& moisture statistics, and Open-Meteo weather forecasts.

```
aquafield/
├── frontend/   React + Vite + TypeScript + shadcn/ui (Tailwind)
└── backend/    FastAPI + SQLAlchemy + MySQL (SQLite dev fallback)
```

## Quick start

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # edit DATABASE_URL when MySQL is ready
uvicorn app.main:app --reload --port 8000
```

The backend boots with a SQLite dev DB (`aquafield_dev.db`) if `DATABASE_URL`
is unset and seeds 5 demo farms around Skopje, Tikvesh, Pelagonia and Polog.

For MySQL:

```env
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/aquafield
```

Then `uvicorn` again — `init_db()` will create the tables if they don't exist.

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env       # defaults to http://localhost:8000
npm run dev
```

Open http://localhost:5173.

## Pages

| Route        | Source                    | What it does |
|--------------|---------------------------|--------------|
| `/`          | `pages/Overview.tsx`      | Farm map, region rollups, headline stats |
| `/dashboard` | `pages/Dashboard.tsx`     | Per-farm cards, NDVI history, water plan |
| `/estimator` | `pages/Estimator.tsx`     | EKF demo with Kc, ET₀, irrigation control |
| `/alerts`    | `pages/Alerts.tsx`        | Severity log + simulated SMS test button |

## How the data flows

1. The frontend calls `GET /farms/` and `GET /farms/readings/all` on every
   tab change and every 5 minutes (TanStack Query `refetchInterval`).
2. Before reading, it calls `POST /farms/refresh`. That endpoint:
   - loops over every farm in MySQL,
   - pulls Open-Meteo weather + (best effort) Sentinel-2 NDVI/NDMI,
   - runs one EKF day step per farm,
   - converts soil-water mm → % and writes a new row to `farm_readings`,
   - generates alerts when crops go stressed.
3. The frontend joins `farms` ⨝ `farm_readings` and renders.

## Backend route map

| Method | Path                          | Notes |
|--------|-------------------------------|-------|
| GET    | `/farms/`                     | List all farms |
| POST   | `/farms/`                     | Create a farm |
| GET    | `/farms/readings/all`         | All readings desc, dashboard joins client-side |
| POST   | `/farms/refresh`              | Refresh cycle (replaces Supabase `refresh-farm-data`) |
| GET    | `/farms/{farm_id}`            | One farm |
| GET    | `/farms/{farm_id}/readings`   | History for one farm |
| GET    | `/alerts/`                    | List alerts |
| POST   | `/alerts/send`                | Create alert (replaces Supabase `send-sms`) |
| POST   | `/alerts/trigger`             | Re-evaluate every farm |
| POST   | `/irrigate/`                  | Log an irrigation event against quota |
| GET    | `/irrigate/usage`             | Per-farm usage summary |
| GET    | `/analytics/system`           | System-wide stats |
| GET    | `/analytics/farms`            | Per-farm stats |
| GET    | `/analytics/fairness`         | Fairness metric (water sharing equality) |
| POST   | `/sentinel/authenticate`      | OAuth2 token from Copernicus |
| POST   | `/sentinel/statistics`        | NDVI + NDMI stats for a bbox |
| POST   | `/weather/test`               | Open-Meteo passthrough |
| GET    | `/estimates/demo`             | EKF demo, all default crops |
| GET    | `/estimates/demo/{crop}`      | EKF demo for one crop |
| GET    | `/estimates/crops/list`       | Supported crops |
| GET    | `/estimates/soil-types/list`  | Supported soil types |
| GET    | `/estimates/{farm_id}`        | Live EKF state for a farm |
| POST   | `/estimates/run`              | Run a single EKF step on demand |
| POST   | `/estimates/water-savings`    | Estimate vs baseline savings |

Browse them interactively at http://localhost:8000/docs.

## Swapping in your real MySQL schema

When your schema lands, replace `backend/app/db_models.py` with ORM classes
matching it. Keep `backend/app/schemas.py` field names stable — that's the
contract the React frontend depends on. If the column names differ, map them
in the schema layer (e.g. via `Field(alias=...)` in Pydantic, or
`mapped_column(name="...")` in SQLAlchemy).

The seeding logic in `backend/app/utils/seed.py` is idempotent (no-op if any
farms already exist), so you can leave it on while iterating.

## Sentinel-2 credentials

Already in `backend/.env.example` (matching what was in the original backend
zip). The data_inputs module accepts both `SENTINEL_*` and `COPERNICUS_*`
variable names.

## Auth

Removed for now per your request. When you're ready to add it back, the
natural seam is a FastAPI dependency that returns the current user, plus
a single `Authorization` header on the frontend's API client wrapper in
`frontend/src/lib/api.ts`.

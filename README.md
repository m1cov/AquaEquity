# AquaField

Smart irrigation dashboard for North Macedonia. React frontend + FastAPI backend
with an Extended Kalman Filter for daily soil-water estimation, Sentinel-2 NDVI
& moisture statistics, and Open-Meteo weather forecasts.

## 💎 Idea

Irrigation water across Southern Europe is a shared, finite resource — but it's allocated as if it weren't. Farmers irrigate on intuition or fixed schedules, water authorities have no real-time picture of usage, and aquifers drain while crops still hit moisture stress because water goes to the wrong field at the wrong time.

**AquaField** is a precision irrigation and water-fairness platform. It uses an **Extended Kalman Filter** to continuously estimate soil moisture and crop water stress at the per-farm level, then produces three things:  
1. Precise irrigation recommendations  
2. Automatic stress alerts  
3. A fairness layer that tracks usage against quotas across a region  

The Kalman approach is the differentiator — instead of threshold rules, it reasons about uncertainty, so irrigation decisions stay conservative when satellite revisits stretch or forecasts diverge from reality.

## 🛰️ EU Space Technologies

AquaField is built on **Copernicus Sentinel-2**, accessed through the Copernicus Data Space Statistical API. We derive **NDVI** as a proxy for canopy development (feeding the crop coefficient and evapotranspiration model) and **NDMI/SWIR indices** as an indirect soil-moisture signal. These enter the EKF as measurement updates with tuned noise to reflect that they're inferred, not directly sensed.

Between passes, the filter propagates state forward using a **soil-water balance** driven by weather data. That's the value-add: a single Sentinel-2 image is a snapshot, but coupled with a state estimator it becomes a continuously-updated picture of every field in the region — even on cloudy days and between revisits.

## 🌊 EU Space for Water

**Challenge #1: Securing equitable and efficient access to water**  

AquaField addresses the "managing water resources" challenge on two levels:  

- **Farm level:** Uncertainty-aware satellite-grounded recommendations replace schedule-based irrigation, with preliminary simulations suggesting meaningful reductions in applied water without yield loss.  
- **Regional level:** Fairness analytics turn aggregate consumption into a transparent metric, giving authorities and cooperatives a basis for setting equitable quotas.  

Protecting a shared resource means reducing total draw and distributing it fairly — AquaField addresses both in one system.

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

# GreenLedger Module 0 — Farm Registration

Module 0 is the farmer-facing registration service.

## What it does

1. Opens an OpenFreeMap map using MapLibre GL JS.
2. Farmer enters their name and farm name.
3. Farmer clicks **Start Drawing** and clicks around the farm boundary.
4. Farmer clicks **Finish Boundary**.
5. The polygon is represented as GeoJSON in EPSG:4326.
6. **Save Farm Boundary** sends the polygon to FastAPI.
7. FastAPI calculates geodesic area, creates a `FARM_...` ID, stores the farm in SQLite, and writes a GeoJSON copy.
8. Module 1 later reads registered farms through `/api/farms`.

## Map provider

This version uses OpenFreeMap with MapLibre GL JS. OpenFreeMap's public instance does not require an API key or registration. Attribution is displayed by the map.

Style: `https://tiles.openfreemap.org/styles/bright`

## Setup

```powershell
pip install -r requirements.txt
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000`.

## Database

SQLite is created automatically at `module0/data/greenledger.db`.

The database has:

- `farms` — registered farm boundary and metadata
- `observations` — dated Module 1 results

The database, not the GeoJSON export file, is the source of truth.

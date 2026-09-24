from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pyproj import Geod

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
FARM_DIR = DATA_DIR / "farms"
DB_PATH = DATA_DIR / "greenledger.db"
FARM_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="GreenLedger Module 0 — Farm Registration", version="3.0.0")
geod = Geod(ellps="WGS84")


class FarmCreate(BaseModel):
    farm_name: str = Field(min_length=1, max_length=120)
    farmer_name: str = Field(min_length=1, max_length=120)
    geometry: dict


class ObservationCreate(BaseModel):
    farm_id: str = Field(min_length=1, max_length=128)
    observation_date: str
    crop: str | None = None
    image_path: str
    satellite_collection: str
    scene_id: str | None = None
    cloud_cover_pct: float | None = None
    mean_ndvi: float
    vegetation_area_m2: float
    vegetation_area_ha: float
    vegetation_coverage_pct: float
    vegetation_health: str
    initial_masks: int
    voted_masks: int
    carbon_score: float
    carbon_unit: str = "tons CO2/ha/yr"
    area_source: str = "NDVI >= 0.1"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS farms (
                farm_id TEXT PRIMARY KEY,
                farm_name TEXT NOT NULL,
                farmer_name TEXT NOT NULL,
                area_ha REAL NOT NULL,
                geometry_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS observations (
                observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id TEXT NOT NULL,
                observation_date TEXT NOT NULL,
                crop TEXT,
                image_path TEXT NOT NULL,
                satellite_collection TEXT NOT NULL,
                scene_id TEXT,
                cloud_cover_pct REAL,
                mean_ndvi REAL NOT NULL,
                vegetation_area_m2 REAL NOT NULL,
                vegetation_area_ha REAL NOT NULL,
                vegetation_coverage_pct REAL NOT NULL,
                vegetation_health TEXT NOT NULL,
                initial_masks INTEGER NOT NULL,
                voted_masks INTEGER NOT NULL,
                carbon_score REAL NOT NULL,
                carbon_unit TEXT NOT NULL,
                area_source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(farm_id, scene_id)
            )
            """
        )
        conn.commit()


init_db()


def validate_polygon(geometry: dict) -> None:
    if geometry.get("type") not in {"Polygon", "MultiPolygon"}:
        raise HTTPException(400, "Farm boundary must be a Polygon or MultiPolygon.")
    if not geometry.get("coordinates"):
        raise HTTPException(400, "Farm boundary has no coordinates.")


def polygon_area_hectares(geometry: dict) -> float:
    """Geodesic WGS84 area in hectares for a GeoJSON Polygon/MultiPolygon."""
    def ring_area(ring):
        if len(ring) < 4:
            return 0.0
        lon = [p[0] for p in ring]
        lat = [p[1] for p in ring]
        area, _ = geod.polygon_area_perimeter(lon, lat)
        return abs(area)

    if geometry["type"] == "Polygon":
        coords = geometry["coordinates"]
        outer = ring_area(coords[0])
        holes = sum(ring_area(r) for r in coords[1:])
        return max(0.0, outer - holes) / 10_000.0

    total = 0.0
    for polygon in geometry["coordinates"]:
        outer = ring_area(polygon[0])
        holes = sum(ring_area(r) for r in polygon[1:])
        total += max(0.0, outer - holes)
    return total / 10_000.0


def row_to_feature(row):
    return {
        "type": "Feature",
        "properties": {
            "farm_id": row["farm_id"],
            "farm_name": row["farm_name"],
            "farmer_name": row["farmer_name"],
            "area_ha": row["area_ha"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "crs": "EPSG:4326",
        },
        "geometry": json.loads(row["geometry_json"]),
    }


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "module": "module0"}



@app.post("/api/farms")
def create_farm(payload: FarmCreate):
    validate_polygon(payload.geometry)
    now = datetime.now(timezone.utc).isoformat()
    farm_id = f"FARM_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    area_ha = polygon_area_hectares(payload.geometry)

    with get_db() as conn:
        conn.execute(
            """INSERT INTO farms
               (farm_id, farm_name, farmer_name, area_ha, geometry_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                farm_id, payload.farm_name, payload.farmer_name,
                area_ha, json.dumps(payload.geometry), now, now,
            ),
        )
        row = conn.execute("SELECT * FROM farms WHERE farm_id = ?", (farm_id,)).fetchone()

    feature = row_to_feature(row)
    (FARM_DIR / f"{farm_id}.geojson").write_text(
        json.dumps(feature, indent=2), encoding="utf-8"
    )

    return {
        "farm_id": farm_id,
        "farm_name": payload.farm_name,
        "farmer_name": payload.farmer_name,
        "area_ha": round(area_ha, 6),
        "geometry": payload.geometry,
    }


@app.get("/api/farms")
def list_farms():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM farms ORDER BY created_at DESC").fetchall()
    return {"count": len(rows), "farms": [row_to_feature(r) for r in rows]}


@app.get("/api/farms/{farm_id}")
def get_farm(farm_id: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM farms WHERE farm_id = ?", (farm_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Farm not found.")
    return row_to_feature(row)


@app.get("/api/farms/{farm_id}/boundary")
def get_farm_boundary(farm_id: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT farm_id, geometry_json FROM farms WHERE farm_id = ?", (farm_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(404, "Farm not found.")
    return {"farm_id": row["farm_id"], "geometry": json.loads(row["geometry_json"]), "crs": "EPSG:4326"}


@app.post("/api/observations")
def save_observation(payload: ObservationCreate):
    # Confirm the farm exists before storing an observation.
    with get_db() as conn:
        farm = conn.execute("SELECT farm_id FROM farms WHERE farm_id = ?", (payload.farm_id,)).fetchone()
        if farm is None:
            raise HTTPException(404, "Farm not found.")
        now = datetime.now(timezone.utc).isoformat()
        try:
            cursor = conn.execute(
                """INSERT INTO observations
                (farm_id, observation_date, crop, image_path, satellite_collection,
                 scene_id, cloud_cover_pct, mean_ndvi, vegetation_area_m2,
                 vegetation_area_ha, vegetation_coverage_pct, vegetation_health,
                 initial_masks, voted_masks, carbon_score, carbon_unit, area_source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    payload.farm_id, payload.observation_date, payload.crop,
                    payload.image_path, payload.satellite_collection, payload.scene_id,
                    payload.cloud_cover_pct, payload.mean_ndvi, payload.vegetation_area_m2,
                    payload.vegetation_area_ha, payload.vegetation_coverage_pct,
                    payload.vegetation_health, payload.initial_masks, payload.voted_masks,
                    payload.carbon_score, payload.carbon_unit, payload.area_source, now,
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            # Duplicate scene for the same farm is idempotent for scheduler retries.
            if payload.scene_id:
                existing = conn.execute(
                    "SELECT * FROM observations WHERE farm_id = ? AND scene_id = ?",
                    (payload.farm_id, payload.scene_id),
                ).fetchone()
                if existing:
                    return {"status": "already_exists", "observation": dict(existing)}
            raise HTTPException(409, f"Observation could not be stored: {exc}")

        row = conn.execute(
            "SELECT * FROM observations WHERE observation_id = ?", (cursor.lastrowid,)
        ).fetchone()

    return {"status": "created", "observation": dict(row)}


@app.get("/api/farms/{farm_id}/observations")
def list_observations(farm_id: str):
    with get_db() as conn:
        farm = conn.execute("SELECT farm_id FROM farms WHERE farm_id = ?", (farm_id,)).fetchone()
        if farm is None:
            raise HTTPException(404, "Farm not found.")
        rows = conn.execute(
            "SELECT * FROM observations WHERE farm_id = ? ORDER BY observation_date DESC",
            (farm_id,),
        ).fetchall()
    return {"farm_id": farm_id, "count": len(rows), "observations": [dict(r) for r in rows]}


@app.get("/api/farms/{farm_id}/observations/latest")
def latest_observation(farm_id: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM observations WHERE farm_id = ? ORDER BY observation_date DESC LIMIT 1",
            (farm_id,),
        ).fetchone()
    if row is None:
        return {"farm_id": farm_id, "observation": None}
    return {"farm_id": farm_id, "observation": dict(row)}
# Add these endpoints to the END of app.py in module0
# (before the last line)

# ── MRV endpoints ─────────────────────────────────────────────

class ProjectCreate(BaseModel):
    baseline_year: int = 2020
    project_start: str = ""
    project_end: str = ""
    methodology: str = "IPCC Tier-1"
    carbon_standard: str = "Voluntary"
    notes: str = ""

class ManagementCreate(BaseModel):
    farming_practice: str = "Conventional"
    tillage_type: str = "Conventional"
    irrigation: str = "Rainfed"
    fertilizer_use: str = "Synthetic"
    cover_crops: bool = False
    agroforestry: bool = False
    notes: str = ""


@app.get("/api/farms/{farm_id}/project")
def get_project(farm_id: str):
    with get_db() as conn:
        farm = conn.execute(
            "SELECT * FROM farms WHERE farm_id = ?", (farm_id,)
        ).fetchone()
    if farm is None:
        raise HTTPException(404, "Farm not found.")
    # Return default project config derived from farm data
    return {
        "farm_id": farm_id,
        "baseline_year": 2020,
        "project_start": farm["created_at"][:10],
        "project_end": "",
        "methodology": "IPCC Tier-1 / SILVIA-SAM",
        "carbon_standard": "Voluntary",
        "area_ha": farm["area_ha"],
        "notes": "Auto-generated from Module 0 farm registration."
    }


@app.get("/api/farms/{farm_id}/management")
def get_management(farm_id: str):
    with get_db() as conn:
        farm = conn.execute(
            "SELECT * FROM farms WHERE farm_id = ?", (farm_id,)
        ).fetchone()
    if farm is None:
        raise HTTPException(404, "Farm not found.")
    # Return default management config
    return {
        "farm_id": farm_id,
        "farming_practice": "Conventional",
        "tillage_type": "Conventional",
        "irrigation": "Rainfed",
        "fertilizer_use": "Synthetic",
        "cover_crops": False,
        "agroforestry": False,
        "notes": "Default management profile. Update via Module 0 UI."
    }


@app.post("/api/farms/{farm_id}/project")
def update_project(farm_id: str, payload: ProjectCreate):
    with get_db() as conn:
        farm = conn.execute(
            "SELECT farm_id FROM farms WHERE farm_id = ?", (farm_id,)
        ).fetchone()
    if farm is None:
        raise HTTPException(404, "Farm not found.")
    return {
        "farm_id": farm_id,
        "status": "updated",
        **payload.dict()
    }


@app.post("/api/farms/{farm_id}/management")
def update_management(farm_id: str, payload: ManagementCreate):
    with get_db() as conn:
        farm = conn.execute(
            "SELECT farm_id FROM farms WHERE farm_id = ?", (farm_id,)
        ).fetchone()
    if farm is None:
        raise HTTPException(404, "Farm not found.")
    return {
        "farm_id": farm_id,
        "status": "updated",
        **payload.dict()
    }
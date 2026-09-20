from __future__ import annotations
from typing import Any
import requests


def _unwrap_json(value: Any):
    if isinstance(value, dict):
        for key in ("observations", "data", "items", "results"):
            if key in value and isinstance(value[key], list):
                return value[key]
    return value


def _get(base: str, path: str):
    r = requests.get(f"{base.rstrip('/')}{path}", timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_farm(module0_url: str, farm_id: str) -> dict:
    data = _get(module0_url, f"/api/farms/{farm_id}")
    return data if isinstance(data, dict) else {"raw": data}


def fetch_observations(module0_url: str, farm_id: str) -> list[dict]:
    data = _unwrap_json(_get(module0_url, f"/api/farms/{farm_id}/observations"))
    return data if isinstance(data, list) else []


def normalize_observation(o: dict) -> dict:
    def first(*keys):
        for k in keys:
            if o.get(k) is not None:
                return o[k]
        return None
    return {
        "date": first("observation_date", "date", "observed_at", "timestamp"),
        "scene_id": first("scene_id", "product_id"),
        "mean_ndvi": first("mean_ndvi", "ndvi_mean"),
        "vegetation_coverage_pct": first("vegetation_coverage_pct", "veg_coverage_pct"),
        "vegetation_area_ha": first("vegetation_area_ha", "veg_area_ha"),
        "vegetation_health": first("vegetation_health", "health_label"),
        "cloud_cover_pct": first("cloud_cover_pct", "cloud_cover"),
        "carbon_score": first("carbon_score", "total_carbon_score"),
        "raw": o,
    }

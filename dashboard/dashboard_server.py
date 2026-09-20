from __future__ import annotations
import argparse, json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from greenledger_asset.observations import fetch_farm, fetch_observations, normalize_observation
from greenledger_asset.asset import build_carbon_asset
from greenledger_asset.ndvi import render_ndvi_png
from greenledger_asset.validation_api import validation_points

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
STATIC = BASE / "static"
MODULE0_URL = "http://127.0.0.1:8000"
app = FastAPI(title="GreenLedger Carbon Asset Dashboard", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def asset_inputs(farm_id):
    p = DATA / "farms" / farm_id / "asset_inputs.json"
    if not p.exists(): return {}
    return json.loads(p.read_text(encoding="utf-8"))


def validation_metrics():
    p = DATA / "validation" / "metrics.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def ensure_ndvi_png(farm_id):
    d = DATA / "farms" / farm_id
    npy = d / "ndvi.npy"
    png = d / "ndvi.png"
    if npy.exists() and (not png.exists() or npy.stat().st_mtime > png.stat().st_mtime):
        render_ndvi_png(npy, png)
    return png if png.exists() else None

@app.get("/api/asset/{farm_id}")
def api_asset(farm_id: str):
    try:
        farm = fetch_farm(MODULE0_URL, farm_id)
        observations = fetch_observations(MODULE0_URL, farm_id)
    except Exception as e:
        raise HTTPException(502, f"Module 0 API unavailable: {e}")
    asset = build_carbon_asset(farm_id, farm, observations, asset_inputs(farm_id))
    return asset

@app.get("/api/observations/{farm_id}")
def api_observations(farm_id: str):
    try:
        obs = fetch_observations(MODULE0_URL, farm_id)
    except Exception as e:
        raise HTTPException(502, f"Module 0 API unavailable: {e}")
    return [normalize_observation(x) for x in obs]

@app.get("/api/validation")
def api_validation():
    return validation_metrics() or {"available": False}

@app.get("/api/validation/points")
def api_validation_points():
    return validation_points(DATA / "validation" / "soc_validation.csv")

@app.get("/api/ndvi/{farm_id}.png")
def api_ndvi(farm_id: str):
    p = ensure_ndvi_png(farm_id)
    if not p: raise HTTPException(404, "No real polygon-clipped NDVI array found for this farm.")
    return FileResponse(p, media_type="image/png")

@app.get("/dashboard/{farm_id}", response_class=HTMLResponse)
def dashboard(farm_id: str):
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    return html.replace("__FARM_ID__", farm_id)

if __name__ == "__main__":
    import uvicorn
    ap=argparse.ArgumentParser(); ap.add_argument("--module0",default="http://127.0.0.1:8000"); ap.add_argument("--host",default="127.0.0.1"); ap.add_argument("--port",type=int,default=8010)
    a=ap.parse_args(); MODULE0_URL=a.module0
    uvicorn.run(app,host=a.host,port=a.port)

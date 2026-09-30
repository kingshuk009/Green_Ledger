from __future__ import annotations
import argparse, json, requests
import pandas as pd
from catboost import CatBoostRegressor
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
SOC_MODEL_DIR = (
    BASE.parent
    / "spatial_carbon_extension"
    / "models"
    / "spatial_soc"
)

SOC_MODEL_FILE = SOC_MODEL_DIR / "spatial_soc_catboost.cbm"
SOC_METADATA_FILE = SOC_MODEL_DIR / "metadata.json"
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
        # First try normal polygon farm
        try:
            farm = fetch_farm(MODULE0_URL, farm_id)
        except Exception:
            # CSV farm fallback
            r = requests.get(
                f"{MODULE0_URL}/api/dataset/farms/{farm_id}",
                timeout=30
            )
            r.raise_for_status()
            dataset = r.json()

            farm = {
                "farm_id": dataset["Farm_ID"],
                "farm_name": dataset["Farm_ID"],
                "area_ha": None,
                "latitude": dataset.get("Latitude"),
                "longitude": dataset.get("Longitude"),
                "crop": dataset.get("Crop"),
                "soil_type": dataset.get("Soil_Type"),
            }

        # Observations
        try:
            observations = fetch_observations(
                MODULE0_URL,
                farm_id
            )
        except Exception:
            observations = []

        # CSV soil/SOC + CatBoost prediction
        soc_data = None
        try:
            r = requests.get(
                f"http://127.0.0.1:8010/api/soc/{farm_id}",
                timeout=30
            )
            if r.ok:
                soc_data = r.json()
        except Exception:
            pass

        inputs = asset_inputs(farm_id)
        # Add farm-specific SOC model evidence
        if soc_data:
            inputs["actual_soc_tC_ha"] = soc_data.get("actual_soc_tC_ha")
            inputs["project_soc_tC_ha"] = soc_data.get("predicted_soc_tC_ha")

            inputs["model_name"] = "CatBoost Spatial SOC"
            inputs["model_version"] = "spatial_soc_catboost"

        # Populate model result for CSV farms
        if soc_data:
            inputs["project_soc_tC_ha"] = soc_data.get(
                "predicted_soc_tC_ha"
            )
            inputs["model_name"] = "CatBoost Spatial SOC"
            inputs["model_version"] = "spatial_soc_catboost"

        # Add validation metrics
        metrics = validation_metrics()

        if metrics and metrics.get("available"):
            inputs["model_validation_mae_tC_ha"] = metrics.get(
                "mae_tC_ha"
            )
            inputs["model_validation_rmse_tC_ha"] = metrics.get(
                "rmse_tC_ha"
            )
            inputs["model_validation_r2"] = metrics.get(
                "r2"
            )

        inputs["methodology_id"] = "GreenLedger Spatial SOC"
        inputs["methodology_version"] = "1.0"
        inputs["limitations"] = [
        "CSV farm has point location rather than a surveyed farm boundary.",
        "Predicted SOC is not treated as measured carbon sequestration.",
        "Carbon outcome requires a documented baseline SOC and farm area."
        ]

        asset = build_carbon_asset(
            farm_id,
            farm,
            observations,
            inputs
        )

        return asset

    except Exception as e:
        raise HTTPException(
            502,
            f"Carbon asset generation failed: {e}"
        )

@app.get("/api/csv-farm/{farm_id}")
def api_csv_farm(farm_id: str):
    try:
        r = requests.get(
            f"{MODULE0_URL}/api/dataset/farms/{farm_id}",
            timeout=30
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise HTTPException(
            502,
            f"CSV farm data unavailable: {e}"
        )

@app.get("/api/soc/{farm_id}")
def api_soc(farm_id: str):
    if not SOC_MODEL_FILE.exists():
        raise HTTPException(404, "Trained SOC model not found.")

    if not SOC_METADATA_FILE.exists():
        raise HTTPException(404, "SOC model metadata not found.")

    try:
        response = requests.get(
            f"{MODULE0_URL}/api/dataset/farms/{farm_id}",
            timeout=30
        )
        response.raise_for_status()
        row = response.json()

        metadata = json.loads(
            SOC_METADATA_FILE.read_text(encoding="utf-8")
        )

        feature_columns = metadata["feature_columns"]
        categorical_columns = metadata.get("categorical_columns", [])

        df = pd.DataFrame([row])

        percent_columns = [
            "Nitrogen - High",
            "Nitrogen - Medium",
            "Nitrogen - Low",
            "Phosphorous - High",
            "Phosphorous - Medium",
            "Phosphorous - Low",
            "Potassium - High",
            "Potassium - Medium",
            "Potassium - Low",
            "pH - Acidic",
            "pH - Neutral",
            "pH - Alkaline",
        ]

        for col in percent_columns:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.replace("%", "", regex=False)
                    .astype(float)
                )

        numeric_columns = [
            "Latitude",
            "Longitude",
            "Fertilizer_Used(tons)",
            "Pesticide_Used(kg)",
            "Yield(tons)",
            "Water_Usage(cubic meters)",
        ]

        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col],
                    errors="coerce"
                )

        X = df.reindex(columns=feature_columns)

        for col in categorical_columns:
            X[col] = X[col].fillna("Missing").astype(str)

        model = CatBoostRegressor()
        model.load_model(str(SOC_MODEL_FILE))

        prediction = float(model.predict(X)[0])

        actual = row.get("SOC_Stock(tC/ha)")

        try:
            actual = float(actual)
        except (TypeError, ValueError):
            actual = None

        return {
            "farm_id": farm_id,
            "actual_soc_tC_ha": actual,
            "predicted_soc_tC_ha": prediction
        }

    except Exception as e:
        raise HTTPException(
            502,
            f"SOC prediction failed: {e}"
        )

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

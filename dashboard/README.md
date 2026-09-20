# GreenLedger — Carbon Asset Presentation Layer

This is a downstream extension for the existing GreenLedger Module 0 and Module 1.
It does **not** replace or regenerate those modules.

## What this adds

For a registered farm, the extension provides a presentation-ready Carbon Asset view with:

1. NDVI / greenery spatial heatmap when a real NDVI raster (`.npy`) is supplied.
2. NDVI temporal trend from Module 0 observation history.
3. Actual-vs-predicted SOC validation scatter from a real validation CSV.
4. Baseline-vs-current SOC comparison.
5. Carbon Asset evidence card with provenance, model information, uncertainty, and status.
6. A clear distinction between an estimated carbon asset and an official issued carbon credit.

## Important integration rule

Module 0 remains the source of truth for farm registration and polygon geometry.
Module 1 remains the source of truth for Sentinel-2 observations and vegetation observations.
This package consumes their APIs and adds a downstream carbon-asset presentation layer.

## Folder layout

```text
D:\GL\
├── module0/                         # existing — untouched
├── module1/                         # existing — untouched
└── carbon_asset_dashboard/          # copy this package here
```

## Install

```bat
cd /d D:\GL\carbon_asset_dashboard
python -m pip install -r requirements.txt
```

## Start dashboard

Assuming Module 0 is running on port 8000:

```bat
cd /d D:\GL\carbon_asset_dashboard
python run_dashboard.py --module0 http://127.0.0.1:8000 --port 8010
```

Open:

```text
http://127.0.0.1:8010/dashboard/FARM_ID
```

Replace `FARM_ID` with a real farm ID from Module 0.

## Carbon Asset input

The dashboard can read an optional per-farm JSON file:

```text
data/farms/FARM_ID/asset_inputs.json
```

Example:

```json
{
  "baseline_soc_tC_ha": 40.8,
  "project_soc_tC_ha": 43.2,
  "soc_uncertainty_pct": 8.0,
  "model_name": "Spatial CatBoost",
  "model_version": "v1.0",
  "model_validation_mae_tC_ha": 3.2,
  "model_validation_rmse_tC_ha": 4.7,
  "model_validation_r2": 0.81,
  "spatial_neighbor_count": 7,
  "nearest_neighbor_km": 12.4,
  "spatial_weighted_soc_tC_ha": 41.9,
  "methodology_id": "VCS-VM0042",
  "methodology_version": "2.2",
  "status": "ESTIMATED"
}
```

The example values are **illustrative only**. Replace them with real measurements/model outputs before presenting them as project results.

## NDVI heatmap

Module 1 already calculates NDVI internally. This downstream package does not rerun Module 1.
To display a real spatial NDVI heatmap, export the polygon-clipped NDVI array as:

```text
data/farms/FARM_ID/ndvi.npy
```

The array must contain real NDVI values in approximately [-1, 1]. The package will render it as a PNG automatically.

For strict scientific presentation, the NDVI array should already be clipped to the registered farm polygon.

## SOC validation scatter

Create:

```text
data/validation/soc_validation.csv
```

with at least:

```csv
actual_soc_tC_ha,predicted_soc_tC_ha
42.1,40.8
38.7,39.9
51.2,49.8
```

Run:

```bat
python scripts/evaluate_soc.py --csv data/validation/soc_validation.csv --out data/validation/metrics.json
```

The dashboard then displays the actual-vs-predicted scatter and MAE/RMSE/R².

Do not use the old prototype Carbon Score as the SOC target.

## What the dashboard communicates

```text
Satellite observations → greenery evidence
                    ↓
Observed soil + spatial evidence + ML → SOC estimate
                    ↓
Baseline vs project SOC → estimated SOC change
                    ↓
Area + CO2 conversion → estimated carbon outcome
                    ↓
Uncertainty + QA/QC + methodology status
                    ↓
CARBON ASSET — ESTIMATE ONLY / MRV REVIEW / etc.
```

The dashboard deliberately does not label an estimate as an issued carbon credit.

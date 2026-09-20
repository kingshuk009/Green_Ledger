# GreenLedger — Final Carbon Asset Minor-Project Package

This package adds the downstream carbon-asset/MRV/presentation layer to the user's existing GreenLedger.

## Preserved modules
- Module 0: existing farm registration and polygon system — NOT regenerated.
- Module 1: existing Sentinel-2 + SAM/SILVIA observation system — NOT regenerated.

## Added downstream capabilities
- Polygon-first spatial SOC architecture.
- Centroid used only as a spatial reference for neighbor evidence.
- Spatially informed CatBoost SOC model adapter.
- SOC stock/change and CO2e conversion utilities.
- Baseline/additionality/leakage/permanence/uncertainty/QA-QC readiness scaffolding.
- Evidence/audit hashing and methodology registry scaffolding.
- Carbon Asset dashboard with:
  1. NDVI/greenery heatmap when a real polygon-clipped NDVI array is supplied.
  2. NDVI time-series from Module 0 observation history.
  3. Actual-vs-predicted SOC validation scatter using a real held-out validation CSV.
  4. Baseline-vs-current SOC comparison.
  5. Carbon Asset evidence card with status, uncertainty, model and spatial evidence.

## Scope
The minor project stops at the **Carbon Asset Estimate / MRV Review** stage.
Marketplace, blockchain, fraud and quantum modules are intentionally deferred.

## Scientific presentation rule
The dashboard distinguishes:
- vegetation evidence (NDVI),
- SOC model prediction,
- estimated CO2e outcome,
- uncertainty,
- methodology/readiness status.

An estimate is not automatically an issued carbon credit.

See `dashboard/README.md` and `dashboard/docs/PRESENTATION_GUIDE.md` for setup and demo instructions.

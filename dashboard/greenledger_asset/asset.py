from __future__ import annotations
from typing import Any
from datetime import datetime, timezone


def _num(x):
    try:
        return float(x) if x is not None else None
    except (TypeError, ValueError):
        return None


def area_ha_from_farm(farm: dict):
    for k in ("area_ha", "farm_area_ha", "geodesic_area_ha"):
        if _num(farm.get(k)) is not None:
            return _num(farm[k])
    return None


def build_carbon_asset(farm_id: str, farm: dict, observations: list[dict], inputs: dict | None = None):
    inputs = inputs or {}
    area = _num(inputs.get("area_ha")) or area_ha_from_farm(farm)
    normalized = []
    for o in observations:
        date = o.get("observation_date") or o.get("date") or o.get("observed_at")
        ndvi = _num(o.get("mean_ndvi"))
        cov = _num(o.get("vegetation_coverage_pct", o.get("veg_coverage_pct")))
        normalized.append({"date": date, "mean_ndvi": ndvi, "coverage": cov})
    normalized = [x for x in normalized if x["mean_ndvi"] is not None or x["date"] is not None]
    normalized.sort(key=lambda x: str(x["date"] or ""))

    baseline = _num(inputs.get("baseline_soc_tC_ha"))
    project = _num(inputs.get("project_soc_tC_ha"))
    uncertainty = _num(inputs.get("soc_uncertainty_pct"))
    soc_change = project - baseline if project is not None and baseline is not None else None
    co2e = soc_change * area * 44.0 / 12.0 if soc_change is not None and area is not None else None
    conservative = co2e * max(0.0, 1.0 - uncertainty / 100.0) if co2e is not None and uncertainty is not None else None

    latest = normalized[-1] if normalized else {}
    status = inputs.get("status") or ("ESTIMATED" if project is not None else "GREENERY_ONLY")

    # Platform score is intentionally separate from carbon quantity.
    # It is a presentation indicator, not a credit amount.
    ndvi_component = None
    if latest.get("mean_ndvi") is not None:
        ndvi_component = max(0.0, min(100.0, (latest["mean_ndvi"] + 1.0) * 50.0))
    score = _num(inputs.get("carbon_score_100"))
    if score is None and ndvi_component is not None and project is not None:
        # Only a neutral presentation index: SOC level is normalized against optional reference bounds.
        lo = _num(inputs.get("soc_reference_low_tC_ha"))
        hi = _num(inputs.get("soc_reference_high_tC_ha"))
        soc_component = ((project - lo) / (hi - lo) * 100.0) if lo is not None and hi is not None and hi > lo else None
        score = 0.60 * max(0.0, min(100.0, soc_component)) + 0.40 * ndvi_component if soc_component is not None else None

    return {
        "result_type": "GREENLEDGER_CARBON_ASSET_ESTIMATE",
        "farm_id": farm_id,
        "farm_name": farm.get("farm_name") or farm.get("name"),
        "area_ha": area,
        "latest_mean_ndvi": latest.get("mean_ndvi"),
        "latest_vegetation_coverage_pct": latest.get("coverage"),
        "ndvi_observation_count": len(normalized),
        "baseline_soc_tC_ha": baseline,
        "project_soc_tC_ha": project,
        "soc_change_tC_ha": soc_change,
        "estimated_removal_tCO2e": co2e,
        "conservative_removal_tCO2e": conservative,
        "uncertainty_pct": uncertainty,
        "carbon_score_100": score,
        "model_name": inputs.get("model_name"),
        "model_version": inputs.get("model_version"),
        "model_validation_mae_tC_ha": _num(inputs.get("model_validation_mae_tC_ha")),
        "model_validation_rmse_tC_ha": _num(inputs.get("model_validation_rmse_tC_ha")),
        "model_validation_r2": _num(inputs.get("model_validation_r2")),
        "spatial_neighbor_count": int(inputs.get("spatial_neighbor_count", 0) or 0),
        "nearest_neighbor_km": _num(inputs.get("nearest_neighbor_km")),
        "spatial_weighted_soc_tC_ha": _num(inputs.get("spatial_weighted_soc_tC_ha")),
        "methodology_id": inputs.get("methodology_id"),
        "methodology_version": inputs.get("methodology_version"),
        "status": status,
        "limitations": inputs.get("limitations", [
            "This is an estimate/presentation asset, not an official issued carbon credit.",
            "Carbon quantity depends on the validity of the SOC model, baseline and MRV evidence.",
        ]),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

from __future__ import annotations

def soc_stock_tC_ha(soc_percent: float, bulk_density_g_cm3: float, depth_cm: float, coarse_fragment_pct: float = 0.0) -> float:
    """SOC stock for the specified soil layer, t C/ha.

    Uses: SOC fraction * bulk density (Mg/m3) * depth (m) * 10,000 m2/ha,
    adjusted by fine-earth fraction. Numerically this is:
    SOC_% * BD_g/cm3 * depth_cm * (1-coarse/100) * 0.1.
    """
    if soc_percent < 0 or bulk_density_g_cm3 <= 0 or depth_cm <= 0:
        raise ValueError("SOC %, bulk density and depth must be valid positive values")
    if not 0 <= coarse_fragment_pct < 100:
        raise ValueError("coarse_fragment_pct must be in [0,100)")
    return soc_percent * bulk_density_g_cm3 * depth_cm * (1 - coarse_fragment_pct / 100.0) * 0.1

def soc_change_tC_ha(project_soc_tC_ha: float, baseline_soc_tC_ha: float) -> float:
    return project_soc_tC_ha - baseline_soc_tC_ha

def carbon_to_co2e(tC: float) -> float:
    return tC * 44.0 / 12.0

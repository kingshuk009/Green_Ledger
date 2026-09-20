def soc_stock_tC_ha(soc_percent, bulk_density_g_cm3,
                    depth_cm=30.0, coarse_fragment_percent=0.0):
    if soc_percent < 0 or bulk_density_g_cm3 <= 0 or depth_cm <= 0:
        raise ValueError("Invalid soil inputs")
    if not 0 <= coarse_fragment_percent < 100:
        raise ValueError("coarse_fragment_percent must be in [0,100)")
    return ((soc_percent/100.0) * bulk_density_g_cm3 * depth_cm * 10.0
            * (1.0 - coarse_fragment_percent/100.0))

def co2e_from_soc_change(delta_soc_tC_ha):
    return float(delta_soc_tC_ha * 44.0 / 12.0)

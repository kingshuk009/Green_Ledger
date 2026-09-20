from greenledger_asset.asset import build_carbon_asset

def test_asset_math():
    a=build_carbon_asset('F1', {'area_ha':10}, [], {'baseline_soc_tC_ha':40,'project_soc_tC_ha':42})
    assert round(a['soc_change_tC_ha'],2)==2
    assert round(a['estimated_removal_tCO2e'],2)==73.33

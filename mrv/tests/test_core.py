from greenledger_mrv.soc import soc_stock_tC_ha, carbon_to_co2e
from greenledger_mrv.spatial import spatial_neighbor_features

def test_soc(): assert round(soc_stock_tC_ha(1.0,1.3,30,0),2)==39.0

def test_co2(): assert round(carbon_to_co2e(12),2)==44.0

def test_spatial():
    r=spatial_neighbor_features(22.57,88.36,[{'lat':22.571,'lon':88.361,'soc_tC_ha':40}]); assert r['neighbor_count']==1

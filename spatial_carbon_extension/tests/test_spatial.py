import pandas as pd
from spatial_carbon.neighbor_features import build_neighbor_features

def test_neighbors():
    o=pd.DataFrame({"latitude":[22.572,22.575],"longitude":[88.362,88.367],
                    "SOC_Stock_0_30cm_tC_ha":[51.2,53.1]})
    x=build_neighbor_features(22.573,88.363,o,"SOC_Stock_0_30cm_tC_ha")
    assert x["neighbor_count"]==2
    assert 51.2 <= x["neighbor_soc_weighted_mean"] <= 53.1

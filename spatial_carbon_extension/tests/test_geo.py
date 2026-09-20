from spatial_carbon.geo import polygon_area_ha, polygon_centroid_latlon

def test_polygon():
    p={"type":"Polygon","coordinates":[[[0,0],[.01,0],[.01,.01],[0,.01],[0,0]]]}
    assert polygon_area_ha(p)>0
    lat,lon=polygon_centroid_latlon(p)
    assert abs(lat-.005)<1e-6 and abs(lon-.005)<1e-6

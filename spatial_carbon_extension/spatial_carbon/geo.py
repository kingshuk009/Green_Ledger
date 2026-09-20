import math
from shapely.geometry import shape
from pyproj import Geod

GEOD = Geod(ellps="WGS84")

def polygon_area_ha(geojson_geometry):
    geom = shape(geojson_geometry)
    if geom.is_empty or not geom.is_valid:
        raise ValueError("Invalid or empty polygon")
    area_m2, _ = GEOD.geometry_area_perimeter(geom)
    return abs(area_m2) / 10000.0

def polygon_centroid_latlon(geojson_geometry):
    # Spatial reference only; never replaces the polygon.
    geom = shape(geojson_geometry)
    if geom.is_empty or not geom.is_valid:
        raise ValueError("Invalid or empty polygon")
    c = geom.centroid
    return float(c.y), float(c.x)

def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((math.radians(lat2-lat1))/2)**2
    a += math.cos(p1)*math.cos(p2)*math.sin((math.radians(lon2-lon1))/2)**2
    return 2*r*math.asin(math.sqrt(a))

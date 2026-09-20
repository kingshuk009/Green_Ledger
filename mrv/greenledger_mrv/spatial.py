from __future__ import annotations
from math import radians, sin, cos, asin, sqrt
from typing import Iterable, Dict, Any, List

EARTH_RADIUS_KM = 6371.0088

def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = radians(lat1), radians(lat2)
    dphi, dlambda = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dphi/2)**2 + cos(p1)*cos(p2)*sin(dlambda/2)**2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))

def spatial_neighbor_features(lat: float, lon: float, observations: Iterable[Dict[str, Any]], radius_km: float = 100.0, power: float = 2.0):
    rows=[]
    for o in observations:
        if o.get('lat') is None or o.get('lon') is None or o.get('soc_tC_ha') is None: continue
        d=haversine_km(lat,lon,float(o['lat']),float(o['lon']))
        if d <= radius_km:
            rows.append((d,float(o['soc_tC_ha'])))
    rows.sort(key=lambda x:x[0])
    if not rows:
        return {'neighbor_count':0,'nearest_distance_km':None,'weighted_soc_tC_ha':None,'neighbor_soc_mean':None,'neighbor_soc_std':None}
    vals=[v for _,v in rows]
    weights=[1/max(d,0.1)**power for d,_ in rows]
    weighted=sum(w*v for w,(_,v) in zip(weights,rows))/sum(weights)
    mean=sum(vals)/len(vals)
    std=(sum((v-mean)**2 for v in vals)/len(vals))**0.5
    return {'neighbor_count':len(rows),'nearest_distance_km':rows[0][0],'weighted_soc_tC_ha':weighted,'neighbor_soc_mean':mean,'neighbor_soc_std':std}

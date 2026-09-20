import argparse, json, pandas as pd
from spatial_carbon.model import SpatialSOCModel
from spatial_carbon.predict import predict_new_polygon

p=argparse.ArgumentParser()
p.add_argument("--model-dir",required=True)
p.add_argument("--observations",required=True)
p.add_argument("--polygon-json",required=True)
p.add_argument("--owner-json",required=True)
p.add_argument("--satellite-json",required=True)
a=p.parse_args()
model=SpatialSOCModel.load(a.model_dir)
obs=pd.read_csv(a.observations)
polygon=json.load(open(a.polygon_json,encoding="utf-8"))
owner=json.load(open(a.owner_json,encoding="utf-8"))
sat=json.load(open(a.satellite_json,encoding="utf-8"))
print(json.dumps(predict_new_polygon(model,polygon,owner,sat,obs),indent=2))

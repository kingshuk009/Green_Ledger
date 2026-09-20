"""Example prediction adapter. Connect this to Module 0 and Module 1 rather than replacing them."""
import argparse, json
from greenledger_mrv.adapter import get_farm,get_observations,get_project,get_management
from greenledger_mrv.spatial import spatial_neighbor_features

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--farm-id',required=True); ap.add_argument('--module0',default='http://127.0.0.1:8000'); args=ap.parse_args()
    farm=get_farm(args.module0,args.farm_id); obs=get_observations(args.module0,args.farm_id); project=get_project(args.module0,args.farm_id); management=get_management(args.module0,args.farm_id)
    print(json.dumps({'farm':farm,'project':project,'management':management,'observations':obs},indent=2,default=str))
    print('\nNext: construct observed-SOC training features and load a trained CatBoost artifact.')
if __name__=='__main__': main()

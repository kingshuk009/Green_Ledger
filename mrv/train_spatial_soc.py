"""Train a spatially-informed CatBoost SOC model from a prepared observed-SOC CSV.

Expected target: SOC_Stock_0_30cm_tC_ha
Do not use synthetic Carbon Score as the target.
Use spatially separated validation in real experiments.
"""
import argparse, json, pandas as pd

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--csv',required=True); ap.add_argument('--out',default='models/spatial_soc.cbm'); args=ap.parse_args()
    from catboost import CatBoostRegressor
    df=pd.read_csv(args.csv)
    target='SOC_Stock_0_30cm_tC_ha'
    if target not in df: raise SystemExit(f'Missing target {target}')
    X=df.drop(columns=[target]); y=df[target]
    cats=[c for c in X.columns if str(X[c].dtype)=='object']
    model=CatBoostRegressor(iterations=500,depth=7,learning_rate=0.05,loss_function='RMSE',verbose=False)
    model.fit(X,y,cat_features=cats)
    model.save_model(args.out)
    print(json.dumps({'model':args.out,'target':target,'rows':len(df),'warning':'Training accuracy is not a standards compliance claim; use spatially separated validation.'},indent=2))
if __name__=='__main__': main()

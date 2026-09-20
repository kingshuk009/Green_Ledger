import argparse
from pathlib import Path
import pandas as pd
from spatial_carbon.model import SpatialSOCModel
from spatial_carbon.validation import spatial_group_cv

CAT = ["Crop_Type","Irrigation_Type","Soil_Type","Season"]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--csv",required=True)
    p.add_argument("--target",default="SOC_Stock_0_30cm_tC_ha")
    p.add_argument("--model-dir",default="models/spatial_soc")
    p.add_argument("--folds",type=int,default=5)
    p.add_argument("--cell-deg",type=float,default=0.5)
    a=p.parse_args()
    df=pd.read_csv(a.csv)
    need={"latitude","longitude",a.target}
    miss=need-set(df.columns)
    if miss: raise SystemExit(f"Missing required columns: {sorted(miss)}")
    features=[c for c in df.columns if c!=a.target]
    cat=[c for c in CAT if c in features]
    scores=spatial_group_cv(df,features,a.target,cat,a.folds,a.cell_deg)
    out=Path(a.model_dir); out.mkdir(parents=True,exist_ok=True)
    scores.to_csv(out/"spatial_cv_results.csv",index=False)
    print(scores)
    model=SpatialSOCModel().fit(df[features],df[a.target],cat)
    model.metadata={"target":a.target,"validation":"spatial GroupKFold",
                    "cell_deg":a.cell_deg,"categorical_columns":cat}
    model.save(out)
    print("Saved:",out)

if __name__=="__main__": main()

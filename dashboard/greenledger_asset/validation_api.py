from pathlib import Path
import pandas as pd

def validation_points(csv_path):
    p=Path(csv_path)
    if not p.exists(): return []
    df=pd.read_csv(p)
    if not {"actual_soc_tC_ha","predicted_soc_tC_ha"}.issubset(df.columns): return []
    return [{"actual":float(a),"predicted":float(b)} for a,b in zip(df.actual_soc_tC_ha,df.predicted_soc_tC_ha)]

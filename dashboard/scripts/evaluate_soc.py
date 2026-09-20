import argparse
from greenledger_asset.validation import save_metrics
ap=argparse.ArgumentParser()
ap.add_argument("--csv",required=True)
ap.add_argument("--out",required=True)
a=ap.parse_args()
print(save_metrics(a.csv,a.out))

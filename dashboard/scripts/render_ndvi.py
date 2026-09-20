import argparse
from greenledger_asset.ndvi import render_ndvi_png
ap=argparse.ArgumentParser()
ap.add_argument("--npy",required=True)
ap.add_argument("--out",required=True)
a=ap.parse_args()
print(render_ndvi_png(a.npy,a.out))

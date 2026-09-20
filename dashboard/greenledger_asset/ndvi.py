from __future__ import annotations
from pathlib import Path
import numpy as np


def load_ndvi(path: str | Path):
    arr = np.load(path)
    arr = np.asarray(arr, dtype=float)
    if arr.ndim != 2:
        raise ValueError("NDVI .npy file must be a 2-D array")
    arr = np.where(np.isfinite(arr), arr, np.nan)
    return np.clip(arr, -1.0, 1.0)


def render_ndvi_png(npy_path: str | Path, png_path: str | Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    arr = load_ndvi(npy_path)
    png_path = Path(png_path)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 5))
    im = ax.imshow(arr, cmap="RdYlGn", vmin=-1, vmax=1)
    ax.set_title("Farm NDVI heatmap")
    ax.axis("off")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="NDVI")
    fig.tight_layout()
    fig.savefig(png_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return png_path

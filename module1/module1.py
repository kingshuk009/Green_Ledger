# GreenLedger Module 1 — work-ready registered-farm observation pipeline

# Core SILVIA/SAM pipeline is based on the provided fixed notebook.

# ==============================================================
# CELL 1 — Imports
# All packages pre-installed in tf210-win environment
# ==============================================================

import os, json, warnings
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
import numpy as np
import cv2
from pathlib import Path
from tqdm.notebook import tqdm
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from scipy import ndimage
from skimage import measure, morphology
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from PIL import Image
import rasterio
from rasterio.enums import Resampling
warnings.filterwarnings('ignore')

# SAM imports
try:
    import torch
    from segment_anything import sam_model_registry, SamAutomaticMaskGenerator
    SAM_AVAILABLE = True
    print(f'✅ SAM available | PyTorch: {torch.__version__}')
    print(f'   GPU: {"✅" if torch.cuda.is_available() else "❌ (CPU mode)"}')
except ImportError:
    SAM_AVAILABLE = False
    print('⚠️  SAM not available - will use fallback segmentation')

print(f'✅ All imports successful')
print(f'   NumPy    : {np.__version__}')
print(f'   OpenCV   : {cv2.__version__}')
print(f'   Rasterio : {rasterio.__version__}')



# ==============================================================
# CELL 2 — Configuration
# All SILVIA parameters from the paper
# ==============================================================

class SILVIAConfig:
    """
    SILVIA pipeline configuration.
    Based on: de Biase et al. (2025)
    """

    # ── Paths ─────────────────────────────────────────────────
    INPUT_DIR      = Path(os.getenv('SILVIA_INPUT_DIR', 'data/input'))
    OUTPUT_DIR     = Path(os.getenv('SILVIA_OUTPUT_DIR', 'data/silvia_results'))
    SAM_CHECKPOINT = Path(os.getenv('SAM_CHECKPOINT', 'models/sam_vit_h_4b8939.pth'))
    SAM_MODEL_TYPE = 'vit_h'

    # ── Sentinel-2 band configuration ──────────────────────────
    S2_BAND_FILES = {
        'blue':  'B02',
        'green': 'B03',
        'red':   'B04',
        'nir':   'B08',
    }
    S2_SCALE_REFLECTANCE = 10000.0

    # ── Preprocessing ─────────────────────────────────────────
    SCALE_PERCENT  = 100       # No resize — 48x48 already small
    TILE_SIZE      = 512
    USE_TILING     = False

    # ── SAM Hyperparameters ────────────────────────────────────
    # Fast mode: run SAM once on RGB; use spectral channels for validation.
    SAM_FAST_MODE            = os.getenv('SAM_FAST_MODE', 'true').lower() == 'true'
    SAM_POINTS_PER_SIDE      = int(os.getenv('SAM_POINTS_PER_SIDE', '16'))
    SAM_CROP_N_LAYERS        = int(os.getenv('SAM_CROP_N_LAYERS', '0'))
    SAM_MIN_MASK_REGION_AREA = int(os.getenv('SAM_MIN_MASK_REGION_AREA', '5'))
    SAM_MAX_INPUT_SIZE       = int(os.getenv('SAM_MAX_INPUT_SIZE', '1024'))
    SPECTRAL_VEG_THRESHOLD   = float(os.getenv('SPECTRAL_VEG_THRESHOLD', '0.10'))
    SPECTRAL_MIN_COVERAGE    = float(os.getenv('SPECTRAL_MIN_COVERAGE', '0.20'))

    # ── Filtering Thresholds (relaxed for small 48x48 tiles) ──
    STABILITY_THRESHOLD      = 0.50  # relaxed from 0.95
    PREDICTED_IOU_THRESHOLD  = 0.50  # relaxed from 0.80
    AREA_QUANTILE_MIN        = 1     # relaxed from 5
    AREA_QUANTILE_MAX        = 99    # relaxed from 80
    ROUNDNESS_MIN            = 0.0   # relaxed for satellite masks
    ROUNDNESS_MAX            = 1.0   # allow valid mask shapes
    ECCENTRICITY_MAX         = 1.0   # relaxed from 0.9

    # ── Vegetation Indices ─────────────────────────────────────
    VEG_INDICES = ['ndvi', 'vari', 'tgi', 'gli', 'ngrdi', 'exg']

    # ── Channels ──────────────────────────────────────────────
    MASTER_CHANNELS = ['rgb']
    SLAVE_CHANNELS  = ['blue', 'exg']

    # ── Voting Policy ──────────────────────────────────────────
    VOTING_IS = 'ALL'
    VOTING_IM = 'ANY'

    # ── Carbon Rates (IPCC, tons CO2/ha/yr) ───────────────────
    CARBON_RATES = {
        'high_veg':   5.5,
        'medium_veg': 2.5,
        'low_veg':    1.8,
        'non_veg':    0.0,
    }

    # ── Spatial config ─────────────────────────────────────────
    FR_MIN_DIAMETER_M  = 1.0
    FR_MAX_DIAMETER_M  = 10.0
    SPATIAL_RESOLUTION = 10.0  # Sentinel-2 10m resolution per pixel


cfg = SILVIAConfig()
cfg.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print('=' * 60)
print('🌿 GREEN LEDGER — SILVIA Pipeline Configuration')
print('=' * 60)
print(f'  Sentinel-2 Input Dir   : {cfg.INPUT_DIR}')
print(f'  SAM Model Type         : {cfg.SAM_MODEL_TYPE}')
print(f'  Scale Percent          : {cfg.SCALE_PERCENT}%')
print(f'  SAM Fast Mode          : {cfg.SAM_FAST_MODE}')
print(f'  SAM Input Max Size     : {cfg.SAM_MAX_INPUT_SIZE}px')
print(f'  SAM Points Per Side    : {cfg.SAM_POINTS_PER_SIDE}')
print(f'  SAM Crop Layers        : {cfg.SAM_CROP_N_LAYERS}')
print(f'  Min Mask Region Area   : {cfg.SAM_MIN_MASK_REGION_AREA}')
print(f'  Stability Threshold    : {cfg.STABILITY_THRESHOLD}')
print(f'  IOU Threshold          : {cfg.PREDICTED_IOU_THRESHOLD}')
print(f'  Area Quantile Range    : [{cfg.AREA_QUANTILE_MIN}, {cfg.AREA_QUANTILE_MAX}]')
print(f'  Roundness Range        : [{cfg.ROUNDNESS_MIN}, {cfg.ROUNDNESS_MAX}]')
print(f'  Eccentricity Max       : {cfg.ECCENTRICITY_MAX}')
print(f'  Voting Policy          : IS={cfg.VOTING_IS}, IM={cfg.VOTING_IM}')
print(f'  Master Channels        : {cfg.MASTER_CHANNELS}')
print(f'  Slave Channels         : {cfg.SLAVE_CHANNELS}')
print(f'  Vegetation Indices     : {cfg.VEG_INDICES}')
print(f'  Spatial Resolution     : {cfg.SPATIAL_RESOLUTION}m/pixel')
print('=' * 60)
print('✅ Config ready')



# ==============================================================
# CELL 3 — Vegetation Indices
# All indices from Table 1 of de Biase et al. (2025)
#
# Index  | Formula                      | Purpose
# -------|------------------------------|---------------------------
# NDVI   | (NIR-R)/(NIR+R)             | NIR-based vegetation
# VARI   | (G-R)/(G+R-B)              | Vegetation density
# TGI    | -0.5*(R-0.39G-0.61B)       | Chlorophyll content
# GLI    | (2G-R-B)/(2G+R+B)          | Green leaf fraction
# NGRDI  | (G-R)/(G+R)                | Vegetation presence
# ExG    | 2G-R-B                      | Excess green (paper: main index)
# ==============================================================

class VegetationIndices:
    """
    Computes all vegetation indices from Table 1 of the paper.
    Input: RGB image float32 [0,1] or uint8 [0,255]
    Output: index map float32 normalised to [0,1] for visualization
    """

    @staticmethod
    def _split_channels(image):
        """Split RGB image into float channels [0,1]"""
        if image.dtype == np.uint8:
            image = image.astype(np.float32) / 255.0
        R = image[:, :, 0].astype(np.float32)
        G = image[:, :, 1].astype(np.float32)
        B = image[:, :, 2].astype(np.float32)
        return R, G, B

    @staticmethod
    def ndvi(image, nir_band=None):
        """
        NDVI = (NIR - R) / (NIR + R)
        If NIR not available, uses Green as proxy (Green - Red) / (Green + Red)
        Range: [-1, 1]
        """
        R, G, B = VegetationIndices._split_channels(image)
        if nir_band is not None:
            NIR = nir_band.astype(np.float32)
        else:
            NIR = G   # Proxy when NIR not available
        index = (NIR - R) / (NIR + R + 1e-8)
        return np.clip(index, -1, 1)

    @staticmethod
    def vari(image):
        """
        VARI = (G - R) / (G + R - B)  [Ref: 22]
        Estimates vegetation density.
        Range: [-1, 1] approx
        """
        R, G, B = VegetationIndices._split_channels(image)
        index = (G - R) / (G + R - B + 1e-8)
        return np.clip(index, -1, 1)

    @staticmethod
    def tgi(image):
        """
        TGI = -0.5 * (R - 0.39*G - 0.61*B)  [Ref: 16, 13]
        Estimates qualitatively the chlorophyll content.
        """
        R, G, B = VegetationIndices._split_channels(image)
        index = -0.5 * (R - 0.39 * G - 0.61 * B)
        # Normalize to [0, 1]
        index = (index - index.min()) / (index.max() - index.min() + 1e-8)
        return index.astype(np.float32)

    @staticmethod
    def gli(image):
        """
        GLI = (2G - R - B) / (2G + R + B)  [Ref: 2]
        Estimates fraction of G relative to red and blue.
        Range: [-1, 1]
        """
        R, G, B = VegetationIndices._split_channels(image)
        index = (2*G - R - B) / (2*G + R + B + 1e-8)
        return np.clip(index, -1, 1)

    @staticmethod
    def ngrdi(image):
        """
        NGRDI = (G - R) / (G + R)  [Ref: 11, 12]
        Estimates vegetation presence.
        Range: [-1, 1]
        """
        R, G, B = VegetationIndices._split_channels(image)
        index = (G - R) / (G + R + 1e-8)
        return np.clip(index, -1, 1)

    @staticmethod
    def exg(image):
        """
        ExG = 2G - R - B  [Ref: 19, 11]
        Excess Green Index - estimates excess green relative to red and blue.
        Used as primary vegetation index in paper's case study.
        """
        R, G, B = VegetationIndices._split_channels(image)
        index = 2*G - R - B
        # Normalize to [0, 1]
        index = (index - index.min()) / (index.max() - index.min() + 1e-8)
        return index.astype(np.float32)

    @staticmethod
    def compute_all(image, nir_band=None):
        """
        Compute all 6 vegetation indices.
        If nir_band is provided (e.g. real Sentinel-2 B08), NDVI uses
        it directly instead of the Green-channel proxy.
        Returns dict of {name: index_map}
        """
        vi = VegetationIndices
        return {
            'ndvi':  vi.ndvi(image, nir_band=nir_band),
            'vari':  vi.vari(image),
            'tgi':   vi.tgi(image),
            'gli':   vi.gli(image),
            'ngrdi': vi.ngrdi(image),
            'exg':   vi.exg(image),
        }

    @staticmethod
    def to_uint8(index_map):
        """Convert index map to uint8 for SAM input"""
        norm = (index_map - index_map.min()) / (index_map.max() - index_map.min() + 1e-8)
        return (norm * 255).astype(np.uint8)

    @staticmethod
    def to_rgb(index_map, colormap=cv2.COLORMAP_JET):
        """Convert index map to 3-channel RGB for SAM input"""
        uint8 = VegetationIndices.to_uint8(index_map)
        return cv2.applyColorMap(uint8, colormap)




# ==============================================================
# CELL 4 — SILVIA Preprocessing Pipeline
# Three categories (from paper Section 3.1):
#   1. Dimensionality Reduction
#   2. Image Enhancement
#   3. Spectral Decomposition
# ==============================================================

class SILVIAPreprocessor:
    """
    SILVIA preprocessing pipeline.
    Prepares satellite image for SAM mask generation.
    Implements all 3 preprocessing categories from the paper.
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.vi  = VegetationIndices()

    # ── CATEGORY 1: Dimensionality Reduction ─────────────────
    def resize(self, image, scale_percent=None):
        """
        Resize image to reduce dimensionality.
        Paper: scale_percent=20 (resize to 20% of original)
        """
        if scale_percent is None:
            scale_percent = self.cfg.SCALE_PERCENT
        H, W = image.shape[:2]
        new_H = int(H * scale_percent / 100)
        new_W = int(W * scale_percent / 100)
        resized = cv2.resize(image, (new_W, new_H), interpolation=cv2.INTER_AREA)
        return resized

    def tile_image(self, image, tile_size=None):
        """
        Divide large image into non-overlapping tiles.
        Paper: used to avoid memory problems.
        """
        if tile_size is None:
            tile_size = self.cfg.TILE_SIZE
        H, W = image.shape[:2]
        tiles = []
        positions = []
        for y in range(0, H, tile_size):
            for x in range(0, W, tile_size):
                tile = image[y:y+tile_size, x:x+tile_size]
                tiles.append(tile)
                positions.append((y, x))
        return tiles, positions

    # ── CATEGORY 2: Image Enhancement ────────────────────────
    def salt_pepper_filter(self, image, kernel_size=3):
        """
        Salt-and-pepper noise removal via median filtering.
        Paper: 'de-noising technique that improves image sharpness
                by removing random light and dark pixels' [Ref 25]
        """
        if len(image.shape) == 3:
            result = np.zeros_like(image)
            for c in range(image.shape[2]):
                result[:,:,c] = cv2.medianBlur(image[:,:,c], kernel_size)
            return result
        return cv2.medianBlur(image, kernel_size)

    def edge_enhancement(self, image, method='laplacian'):
        """
        Edge enhancement for highlighting object boundaries.
        Paper: 'Sobel, Laplacian filters useful for highlighting
                object boundaries and structures'
        """
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if len(image.shape)==3 else image

        if method == 'laplacian':
            edges = cv2.Laplacian(gray, cv2.CV_64F)
            edges = np.abs(edges).astype(np.uint8)
        elif method == 'sobel':
            sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            edges  = np.sqrt(sobelx**2 + sobely**2)
            edges  = (edges / edges.max() * 255).astype(np.uint8)
        else:
            edges = gray

        # Add edges back to image
        if len(image.shape) == 3:
            edges_3ch = np.stack([edges, edges, edges], axis=-1)
            enhanced  = cv2.addWeighted(image, 0.8, edges_3ch, 0.2, 0)
        else:
            enhanced  = cv2.addWeighted(image, 0.8, edges, 0.2, 0)

        return enhanced

    def contrast_adjustment(self, image):
        """
        CLAHE contrast adjustment.
        Paper: 'distributes intensity values more frequently,
                improving visibility of details in low-contrast areas'
        """
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))

        if len(image.shape) == 3:
            lab    = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
            lab[:,:,0] = clahe.apply(lab[:,:,0])
            enhanced   = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
        else:
            enhanced = clahe.apply(image)

        return enhanced

    # ── CATEGORY 3: Spectral Decomposition ───────────────────
    def split_channels(self, image):
        """
        Split RGB image into individual channels.
        Paper: 'R, G, B channels extracted and saved separately'
        Returns dict: {'red': ..., 'green': ..., 'blue': ...}
        """
        return {
            'red':   image[:, :, 0],
            'green': image[:, :, 1],
            'blue':  image[:, :, 2],  # Paper uses Blue channel
        }

    def compute_vegetation_indices(self, image, nir_band=None):
        """
        Compute all vegetation indices (Table 1 from paper).
        Pass nir_band (real Sentinel-2 B08, resized to match `image`)
        to get true NDVI instead of the Green-channel proxy.
        Returns dict of {name: index_map}
        """
        return VegetationIndices.compute_all(image, nir_band=nir_band)

    # ── Full Preprocessing Pipeline ───────────────────────────
    def preprocess(self, image_path_or_array,
                   apply_salt_pepper=True,
                   apply_edge=False,
                   apply_contrast=True,
                   nir_band=None):
        """
        Full SILVIA preprocessing pipeline.
        Returns dict of all image representations for SAM.

        nir_band: optional (H,W) float32 array [0,1], real NIR reflectance
                  (e.g. from Sentinel2Loader). If given, it is resized to
                  match the post-resize RGB image and used for true NDVI.
        """

        # Load image
        if isinstance(image_path_or_array, (str, Path)):
            image = cv2.imread(str(image_path_or_array))
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image = image_path_or_array.copy()
            if image.dtype == np.float32:
                image = (image * 255).astype(np.uint8)

        print(f'  Original size: {image.shape}')

        # ── STEP 1: Dimensionality Reduction ──
        image = self.resize(image)
        print(f'  After resize ({self.cfg.SCALE_PERCENT}%): {image.shape}')

        # ── STEP 2: Image Enhancement ──
        if apply_salt_pepper:
            image = self.salt_pepper_filter(image)
        if apply_edge:
            image = self.edge_enhancement(image)
        if apply_contrast:
            image = self.contrast_adjustment(image)

        # ── STEP 3: Spectral Decomposition ──
        channels = self.split_channels(image)

        nir_resized = None
        if nir_band is not None:
            nir_resized = cv2.resize(
                nir_band, (image.shape[1], image.shape[0]),
                interpolation=cv2.INTER_AREA
            )
        indices = self.compute_vegetation_indices(image, nir_band=nir_resized)

        # ── Build all SAM input representations ──
        # Paper uses: RGB image, B channel, ExG index
        representations = {}

        # RGB (original - 3 channel)
        representations['rgb'] = image

        # Individual channels (convert to 3-ch for SAM)
        for ch_name, ch_data in channels.items():
            representations[ch_name] = np.stack(
                [ch_data, ch_data, ch_data], axis=-1)

        # Vegetation indices (convert to 3-ch colormap for SAM)
        for idx_name, idx_data in indices.items():
            representations[idx_name] = VegetationIndices.to_rgb(idx_data)

        print(f'  Representations created: {list(representations.keys())}')
        return image, representations, indices


preprocessor = SILVIAPreprocessor(cfg)
print('✅ SILVIA Preprocessor ready')
print('   Steps: Resize → Salt-Pepper → Contrast → Channel Split → VI Compute')



# ==============================================================
# CELL 5 — SAM Mask Generation
# Apply SAM to multiple image representations
# Each mask gets: segmentation, area, predicted_iou,
#                 stability_score, roundness, eccentricity
# ==============================================================

class SAMMaskGenerator:
    """
    SAM mask generator for SILVIA pipeline.
    Applies SAM to multiple image representations.
    Enriches masks with geometric features (Table 2 from paper).
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.generator = None
        self._load_sam()

    def _load_sam(self):
        """Load SAM model"""
        if not SAM_AVAILABLE:
            print('⚠️  SAM not available - using fallback segmentation')
            return

        checkpoint = self.cfg.SAM_CHECKPOINT
        if not checkpoint.exists():
            print(f'⚠️  SAM checkpoint not found at {checkpoint}')
            print('   Download from: https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth')
            print('   Using fallback segmentation')
            return

        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        sam    = sam_model_registry[self.cfg.SAM_MODEL_TYPE](checkpoint=str(checkpoint))
        sam.to(device=device)

        self.generator = SamAutomaticMaskGenerator(
            model=sam,
            points_per_side=self.cfg.SAM_POINTS_PER_SIDE,
            crop_n_layers=self.cfg.SAM_CROP_N_LAYERS,
            min_mask_region_area=self.cfg.SAM_MIN_MASK_REGION_AREA,
        )
        print(f'✅ SAM loaded on {device}')

    # ── Geometric Features (Table 2 from paper) ───────────────
    def compute_area_m2(self, mask_array, spatial_resolution=None):
        """
        Convert pixel area to m².
        Paper: 'Area in m²: converted from pixels to m²
                based on image spatial resolution'
        """
        if spatial_resolution is None:
            spatial_resolution = self.cfg.SPATIAL_RESOLUTION
        pixel_count = np.sum(mask_array)
        return float(pixel_count * (spatial_resolution ** 2))

    def compute_roundness(self, mask_array):
        """
        Roundness = 4π * Area / Perimeter²
        Paper: 'evaluates smoothness and compactness of shape;
                values close to 1 indicate more regular, circular shapes'
        Range: [0, 1]
        """
        mask_uint8 = mask_array.astype(np.uint8)
        contours, _ = cv2.findContours(
            mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return 0.0

        contour   = max(contours, key=cv2.contourArea)
        area      = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)

        if perimeter == 0:
            return 0.0

        roundness = (4 * np.pi * area) / (perimeter ** 2)
        return float(np.clip(roundness, 0, 1))

    def compute_eccentricity(self, mask_array):
        """
        Eccentricity from fitted ellipse.
        Paper: 'quantifies elongation of white pixel distribution;
                values close to 0 indicate circularity;
                values near 1 denote more elongated, elliptical shapes'
        Range: [0, 1]
        """
        mask_uint8 = mask_array.astype(np.uint8)
        contours, _ = cv2.findContours(
            mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return 1.0

        contour = max(contours, key=cv2.contourArea)

        if len(contour) < 5:
            return 1.0

        try:
            ellipse = cv2.fitEllipse(contour)
            a = max(ellipse[1]) / 2   # Semi-major axis
            b = min(ellipse[1]) / 2   # Semi-minor axis
            if a == 0:
                return 1.0
            eccentricity = np.sqrt(1 - (b/a)**2)
            return float(np.clip(eccentricity, 0, 1))
        except Exception:
            return 1.0

    def enrich_mask(self, mask_dict, channel_name):
        """
        Add geometric features to SAM mask (Table 2 from paper).
        Adds: area_m2, roundness, eccentricity, channel_source
        """
        seg = mask_dict['segmentation']
        mask_dict['area_m2']        = self.compute_area_m2(seg)
        mask_dict['roundness']      = self.compute_roundness(seg)
        mask_dict['eccentricity']   = self.compute_eccentricity(seg)
        mask_dict['channel_source'] = channel_name
        return mask_dict

    def _resize_for_sam(self, image):
        """Downsample only the image sent to SAM."""
        if image is None or not isinstance(image, np.ndarray):
            return image
        h, w = image.shape[:2]
        max_size = int(self.cfg.SAM_MAX_INPUT_SIZE)
        if max(h, w) <= max_size:
            return image
        scale = max_size / float(max(h, w))
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

    def _make_spectral_validation_mask(self, base_mask, channel_name, representations, indices):
        """Validate an RGB-SAM mask using spectral evidence instead of another SAM pass."""
        seg = np.asarray(base_mask['segmentation']).astype(bool)
        if channel_name == 'exg':
            spectral = indices.get('exg')
        elif channel_name == 'blue':
            spectral = indices.get('ndvi')
        else:
            return None
        if spectral is None:
            return None
        spectral = np.asarray(spectral, dtype=np.float32)
        if spectral.shape != seg.shape:
            spectral = cv2.resize(spectral, (seg.shape[1], seg.shape[0]), interpolation=cv2.INTER_LINEAR)
        veg = np.isfinite(spectral) & (spectral >= self.cfg.SPECTRAL_VEG_THRESHOLD)
        mask_pixels = int(seg.sum())
        if mask_pixels == 0:
            return None
        coverage = float((seg & veg).sum()) / float(mask_pixels)
        if coverage < self.cfg.SPECTRAL_MIN_COVERAGE:
            return None
        validated = dict(base_mask)
        validated['segmentation'] = seg & veg
        validated['area'] = int(validated['segmentation'].sum())
        validated['channel_source'] = channel_name
        validated['spectral_validation_coverage'] = coverage
        if validated['area'] == 0:
            return None
        return self.enrich_mask(validated, channel_name)

    def generate_masks_sam(self, image, channel_name):
        """Generate SAM masks, optionally using a smaller SAM-only input."""
        if self.generator is None:
            return self._fallback_segmentation(image, channel_name)
        if image.dtype != np.uint8:
            image = np.clip(image * 255.0, 0, 255).astype(np.uint8)
        if len(image.shape) == 2:
            image = np.stack([image, image, image], axis=-1)
        sam_image = self._resize_for_sam(image)
        masks = self.generator.generate(sam_image)
        if sam_image.shape[:2] != image.shape[:2]:
            H, W = image.shape[:2]
            for m in masks:
                m['segmentation'] = cv2.resize(
                    m['segmentation'].astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST
                ).astype(bool)
        return [self.enrich_mask(m, channel_name) for m in masks]

    def _fallback_segmentation(self, image, channel_name):
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if len(image.shape)==3 else image
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        masks = []
        H, W = gray.shape
        for contour in contours:
            mask_arr = np.zeros((H, W), dtype=bool)
            cv2.fillPoly(mask_arr.view(np.uint8), [contour], 1)
            masks.append(self.enrich_mask({
                'segmentation': mask_arr, 'area': int(np.sum(mask_arr)),
                'predicted_iou': 0.85, 'stability_score': 0.90,
                'bbox': cv2.boundingRect(contour)}, channel_name))
        return masks

    def generate_all(self, representations, indices=None):
        """Run SAM once in fast mode; retain Blue/ExG as spectral validation roles."""
        all_masks = {}
        if self.cfg.SAM_FAST_MODE and 'rgb' in representations:
            print('  ⚡ Fast Mode: running SAM once on RGB...')
            rgb_masks = self.generate_masks_sam(representations['rgb'], 'rgb')
            all_masks['rgb'] = rgb_masks
            print(f'  rgb          : {len(rgb_masks)} masks generated')
            indices = indices or {}
            for ch_name in ('blue', 'exg'):
                if ch_name in self.cfg.SLAVE_CHANNELS:
                    validated = [self._make_spectral_validation_mask(m, ch_name, representations, indices) for m in rgb_masks]
                    validated = [m for m in validated if m is not None]
                    all_masks[ch_name] = validated
                    print(f'  {ch_name:<12}: {len(validated)} spectral-validation masks')
            print(f'  Total masks/candidates: {sum(len(v) for v in all_masks.values())}')
            return all_masks
        for ch_name, img in representations.items():
            print(f'  Generating masks for channel: {ch_name}...', end=' ')
            masks = self.generate_masks_sam(img, ch_name)
            all_masks[ch_name] = masks
            print(f'{len(masks)} masks generated')
        print(f'  Total masks generated: {sum(len(v) for v in all_masks.values())}')
        return all_masks



mask_generator = SAMMaskGenerator(cfg)
print('\n✅ SAM Mask Generator ready')
print('   Table 2 features: segmentation, area, predicted_iou, '
      'stability_score, area_m2, roundness, eccentricity')



# ==============================================================
# CELL 6 — SILVIA Filtering Step
# Four filters from paper Section 3.1:
#   1. Quality filtering  (predicted_iou + stability_score)
#   2. Area filtering     (quantile-based 5th-80th percentile)
#   3. Roundness filtering (0.7 - 0.9)
#   4. Eccentricity filtering (<0.9)
# ==============================================================

class SILVIAFilter:
    """
    SILVIA multi-stage mask filtering.
    All filters from paper Section 3.1 (Filtering Step).
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.filter_stats = {}

    def quality_filter(self, masks):
        """
        FILTER 1: Quality filtering.
        Paper: 'only masks with high predicted_iou and
                stability_score are retained'
        """
        filtered = [
            m for m in masks
            if (m.get('stability_score', 0) >= self.cfg.STABILITY_THRESHOLD and
                m.get('predicted_iou', 0)   >= self.cfg.PREDICTED_IOU_THRESHOLD)
        ]
        return filtered

    def area_filter(self, masks):
        """
        FILTER 2: Area filtering.
        Paper: 'masks with area outside specified physical range
                are discarded; quantile-based approach to avoid
                arbitrary values; quantile range fixed to (5, 80)'
        """
        if not masks:
            return masks

        areas = np.array([m.get('area_m2', m.get('area', 0)) for m in masks])

        # Quantile-based thresholds (paper: 5th and 80th percentile)
        area_min = np.percentile(areas, self.cfg.AREA_QUANTILE_MIN)
        area_max = np.percentile(areas, self.cfg.AREA_QUANTILE_MAX)

        filtered = [
            m for m in masks
            if area_min <= m.get('area_m2', m.get('area', 0)) <= area_max
        ]
        return filtered

    def roundness_filter(self, masks):
        """
        FILTER 3: Roundness filtering.
        Paper: 'masks with low roundness (lakes, clouds) or
                elongated shapes (buildings) are filtered out;
                min_threshold=0.7, max_threshold=0.9'
        """
        filtered = [
            m for m in masks
            if self.cfg.ROUNDNESS_MIN <= m.get('roundness', 0) <= self.cfg.ROUNDNESS_MAX
        ]
        return filtered

    def eccentricity_filter(self, masks):
        """
        FILTER 4: Eccentricity filtering.
        Paper: 'elongated and rectangular shapes (e.g., buildings)
                are filtered out, focusing on circular patterns'
        """
        filtered = [
            m for m in masks
            if m.get('eccentricity', 1.0) <= self.cfg.ECCENTRICITY_MAX
        ]
        return filtered

    def filter_channel(self, masks, channel_name,
                       apply_quality=True,
                       apply_area=True,
                       apply_roundness=True,
                       apply_eccentricity=True):
        """
        Apply all 4 filters to one channel's masks.
        Returns filtered masks and statistics.
        """
        stats = {'channel': channel_name, 'initial': len(masks)}

        if apply_quality:
            masks = self.quality_filter(masks)
            stats['after_quality'] = len(masks)

        if apply_area:
            masks = self.area_filter(masks)
            stats['after_area'] = len(masks)

        if apply_roundness:
            masks = self.roundness_filter(masks)
            stats['after_roundness'] = len(masks)

        if apply_eccentricity:
            masks = self.eccentricity_filter(masks)
            stats['after_eccentricity'] = len(masks)

        stats['final'] = len(masks)
        return masks, stats

    def filter_all(self, all_masks):
        """
        Apply filters to all channels.
        Returns dict of {channel_name: filtered_masks}
        """
        filtered_all = {}
        all_stats    = []

        print('\n🔍 SILVIA Filtering Step:')
        print(f'   Thresholds:')
        print(f'     Stability    : ≥ {self.cfg.STABILITY_THRESHOLD}')
        print(f'     Predicted IoU: ≥ {self.cfg.PREDICTED_IOU_THRESHOLD}')
        print(f'     Area Quantile: [{self.cfg.AREA_QUANTILE_MIN}, {self.cfg.AREA_QUANTILE_MAX}]')
        print(f'     Roundness    : [{self.cfg.ROUNDNESS_MIN}, {self.cfg.ROUNDNESS_MAX}]')
        print(f'     Eccentricity : ≤ {self.cfg.ECCENTRICITY_MAX}')
        print()

        for ch_name, masks in all_masks.items():
            filtered, stats = self.filter_channel(masks, ch_name)
            filtered_all[ch_name] = filtered
            all_stats.append(stats)

            print(f'   {ch_name:<12}: '
                  f'{stats["initial"]:>4} → '
                  f'quality:{stats.get("after_quality","?"):>4} → '
                  f'area:{stats.get("after_area","?"):>4} → '
                  f'round:{stats.get("after_roundness","?"):>4} → '
                  f'ecc:{stats["final"]:>4} (final)')

            if stats["initial"] > 0 and stats["final"] == 0:
                print(f'      ⚠ {ch_name}: all masks removed during filtering.')
                if stats.get("after_quality", 0) == 0:
                    print('        Reason: quality thresholds.')
                elif stats.get("after_area", 0) == 0:
                    print('        Reason: area quantile filter.')
                elif stats.get("after_roundness", 0) == 0:
                    print('        Reason: roundness filter.')
                elif stats.get("after_eccentricity", 0) == 0:
                    print('        Reason: eccentricity filter.')

        return filtered_all, all_stats


silvia_filter = SILVIAFilter(cfg)
print('✅ SILVIA Filter ready')
print('   Filters: Quality → Area → Roundness → Eccentricity')



# ==============================================================
# CELL 7 — SILVIA Channels Fusion (Voting Mechanism)
# From paper Section 3.1 - Channels Fusion Step
#
# Master-Slave structure:
#   Masters: high reliability channels (e.g., RGB)
#   Slaves:  diversity channels (e.g., B-channel, ExG)
#
# Voting Policies (Table 3 from paper):
#   IS=ALL + IM=ANY → reduce False Negatives
#   IS=ANY + IM=ALL → reduce False Positives
#
# Operators:
#   ANY: union of masks
#   ALL: intersection of masks
# ==============================================================

class SILVIAMaskFusion:
    """
    SILVIA mask voting/fusion mechanism.
    Implements Algorithm 1 from the paper.
    """

    def __init__(self, cfg):
        self.cfg = cfg

    def masks_overlap(self, mask1, mask2, iou_threshold=0.3):
        """
        Check if two masks overlap (IoU > threshold).
        Used in ALL operator (intersection).
        """
        seg1 = mask1['segmentation'].astype(bool)
        seg2 = mask2['segmentation'].astype(bool)

        # Resize if different shapes
        if seg1.shape != seg2.shape:
            h = min(seg1.shape[0], seg2.shape[0])
            w = min(seg1.shape[1], seg2.shape[1])
            seg1 = seg1[:h, :w]
            seg2 = seg2[:h, :w]

        intersection = np.logical_and(seg1, seg2).sum()
        union        = np.logical_or(seg1, seg2).sum()

        if union == 0:
            return False

        iou = intersection / union
        return iou >= iou_threshold

    def operator_any(self, channel_a, channel_b):
        """
        ANY operator: union of masks.
        Paper: 'result contains union of masks of operands'
        ANY(X, Y) = {mask | mask ∈ X ∨ mask ∈ Y}
        """
        # Simple union: combine all masks from both channels
        return channel_a + channel_b

    def operator_all(self, channel_a, channel_b):
        """
        ALL operator: intersection of masks.
        Paper: 'result contains intersection of masks of operands'
        ALL(X, Y) = {mask | mask ∈ X ∧ mask ∈ Y}
        A mask is kept only if it overlaps with a mask in the other channel.
        """
        if not channel_a or not channel_b:
            return []

        kept = []
        for mask_a in channel_a:
            # Keep mask if it overlaps with any mask in channel_b
            has_overlap = any(
                self.masks_overlap(mask_a, mask_b)
                for mask_b in channel_b
            )
            if has_overlap:
                kept.append(mask_a)
        return kept

    def apply_operator(self, channel_a, channel_b, operator):
        """Apply ANY or ALL operator"""
        if operator == 'ANY':
            return self.operator_any(channel_a, channel_b)
        elif operator == 'ALL':
            return self.operator_all(channel_a, channel_b)
        else:
            raise ValueError(f'Unknown operator: {operator}')

    def fuse(self, filtered_masks):
        """
        Algorithm 1 from the paper: Master-Slave voting mechanism.

        Steps:
        1. Merge all slave channels using IS operator → mx
        2. mx is promoted to master
        3. Merge mx with all master channels using IM operator → voted masks

        Voting Policies (Table 3):
          IS=ALL + IM=ANY → reduce False Negatives
            V = ∑Mi + ∏Si  (keep masks in slaves OR confirmed by master)
          IS=ANY + IM=ALL → reduce False Positives
            V = ∏(Mi · ∑Si)  (keep only masks confirmed by master)
        """

        IS_op = self.cfg.VOTING_IS   # 'ALL' or 'ANY'
        IM_op = self.cfg.VOTING_IM   # 'ALL' or 'ANY'

        master_chs = self.cfg.MASTER_CHANNELS
        slave_chs  = self.cfg.SLAVE_CHANNELS

        print(f'\n🗳️  SILVIA Mask Fusion (Voting)')
        print(f'   Policy: IS={IS_op} + IM={IM_op}')
        if IS_op == 'ALL' and IM_op == 'ANY':
            print(f'   Mode  : False Negative Reduction')
        else:
            print(f'   Mode  : False Positive Reduction')
        print(f'   Masters: {master_chs}')
        print(f'   Slaves : {slave_chs}')

        # Get slave masks (only channels that exist in filtered_masks)
        slave_masks = [
            filtered_masks.get(ch, [])
            for ch in slave_chs
            if ch in filtered_masks
        ]

        # Get master masks
        master_masks = [
            filtered_masks.get(ch, [])
            for ch in master_chs
            if ch in filtered_masks
        ]

        # ── Algorithm 1 Steps 3-6: Merge slave channels ──
        # mx ← s1
        if slave_masks:
            mx = slave_masks[0].copy()
            # for si ∈ S: mx ← R_IS(mx, si)
            for si in slave_masks[1:]:
                mx = self.apply_operator(mx, si, IS_op)
        else:
            mx = []

        print(f'   After slave merge ({IS_op}): {len(mx)} masks')
        if not mx:
            print('   ⚠ Fusion warning: no slave masks survived.')

        # ── Algorithm 1 Steps 7-10: Merge mx with masters ──
        # v ← mx (promote mx to master)
        v = mx
        # for mi ∈ M: v ← R_IM(v, mi)
        for mi in master_masks:
            v = self.apply_operator(v, mi, IM_op)

        print(f'   After master merge ({IM_op}): {len(v)} voted masks')

        return v

    def create_pattern_image(self, voted_masks, image_shape):
        """
        Create 'pattern detected' image from voted masks.
        Paper: 'voted masks merged → composite pattern detected image'
        """
        H, W = image_shape[:2]
        pattern = np.zeros((H, W), dtype=np.uint8)

        colors = np.random.randint(50, 255, (len(voted_masks), 3), dtype=np.uint8)
        pattern_colored = np.zeros((H, W, 3), dtype=np.uint8)

        for i, mask in enumerate(voted_masks):
            seg = mask['segmentation'].astype(bool)
            if seg.shape != (H, W):
                seg = cv2.resize(seg.astype(np.uint8), (W, H),
                                 interpolation=cv2.INTER_NEAREST).astype(bool)
            pattern[seg] = 255
            pattern_colored[seg] = colors[i]

        return pattern, pattern_colored


mask_fusion = SILVIAMaskFusion(cfg)
print('✅ SILVIA Mask Fusion ready')
print('   Algorithm 1 from paper: Master-Slave voting mechanism')
print(f'   Current policy: IS={cfg.VOTING_IS} + IM={cfg.VOTING_IM}')



# ==============================================================
# CELL 8 — Carbon Score Engine (FIXED)
# Converts SILVIA voted masks + true Sentinel-2 NDVI → Carbon Score
# ==============================================================

class CarbonEngine:
    """
    Robust carbon/vegetation-area engine.

    Fixes:
      1. Vegetation area is calculated from the actual NDVI map.
      2. Overlapping masks are counted only once for vegetation area.
      3. Sentinel-2 pixel area is converted using spatial resolution.
      4. If mask voting returns no masks, NDVI still provides a
         vegetation-area estimate instead of returning zero.
    """

    def __init__(self, cfg):
        self.cfg = cfg

    def classify_vegetation_density(self, ndvi_value):
        """Classify vegetation density and assign the configured rate."""
        if ndvi_value >= 0.6:
            return 'high_veg', self.cfg.CARBON_RATES['high_veg']
        elif ndvi_value >= 0.3:
            return 'medium_veg', self.cfg.CARBON_RATES['medium_veg']
        elif ndvi_value >= 0.1:
            return 'low_veg', self.cfg.CARBON_RATES['low_veg']
        else:
            return 'non_veg', self.cfg.CARBON_RATES['non_veg']

    def _prepare_ndvi(self, ndvi_map, target_shape=None):
        """Clean NDVI and optionally resize it to a target mask shape."""
        if ndvi_map is None:
            return None

        ndvi = np.asarray(ndvi_map, dtype=np.float32)

        # Remove invalid numerical values.
        ndvi = np.nan_to_num(ndvi, nan=0.0, posinf=1.0, neginf=-1.0)
        ndvi = np.clip(ndvi, -1.0, 1.0)

        if target_shape is not None and ndvi.shape != target_shape:
            ndvi = cv2.resize(
                ndvi,
                (target_shape[1], target_shape[0]),
                interpolation=cv2.INTER_LINEAR
            )
            ndvi = np.clip(ndvi, -1.0, 1.0)

        return ndvi

    def compute_mask_carbon(self, mask, ndvi_map):
        """
        Compute carbon score for one voted mask using mean NDVI.
        """
        seg = np.asarray(mask['segmentation']).astype(bool)

        ndvi = self._prepare_ndvi(ndvi_map, seg.shape)

        if ndvi is None or not seg.any():
            return 0.0, 'non_veg', 0.0

        mean_ndvi = float(ndvi[seg].mean())

        # Prefer the actual segmentation pixel count over a possibly
        # stale/missing area_m2 field.
        pixel_count = int(seg.sum())
        pixel_area_m2 = self.cfg.SPATIAL_RESOLUTION ** 2
        calculated_area_m2 = pixel_count * pixel_area_m2

        area_m2 = float(mask.get('area_m2', 0.0))
        if area_m2 <= 0:
            area_m2 = calculated_area_m2

        area_ha = area_m2 / 10000.0

        veg_class, rate = self.classify_vegetation_density(mean_ndvi)
        carbon_score = rate * area_ha

        return carbon_score, veg_class, mean_ndvi

    def _ndvi_vegetation_area(self, ndvi_map):
        """
        Calculate vegetation area directly from NDVI.

        NDVI >= 0.1 is treated as vegetation, matching the
        low_veg threshold used by classify_vegetation_density().
        """
        if ndvi_map is None:
            return 0.0, 0.0, np.zeros((0, 0), dtype=bool)

        ndvi = self._prepare_ndvi(ndvi_map)
        veg_mask = ndvi >= 0.1

        pixel_area_m2 = self.cfg.SPATIAL_RESOLUTION ** 2
        veg_area_m2 = float(veg_mask.sum() * pixel_area_m2)

        return (
            veg_area_m2,
            float(veg_mask.mean() * 100.0),
            veg_mask
        )

    def compute_total_carbon(self, voted_masks, ndvi_map, area_ha=None):
        """
        Compute total carbon score and vegetation area.

        Vegetation area is based on the UNION of vegetation portions
        of voted masks. If there are no voted masks, it falls back
        to the complete NDVI vegetation map.
        """
        ndvi = self._prepare_ndvi(ndvi_map)

        # Ground-truth-ish vegetation estimate from NDVI.
        ndvi_veg_area_m2, ndvi_veg_pct, ndvi_veg_mask = \
            self._ndvi_vegetation_area(ndvi)

        breakdown = []
        total_carbon = 0.0
        ndvi_values = []

        # Union of vegetation pixels represented by voted masks.
        union_veg_mask = (
            np.zeros_like(ndvi, dtype=bool) if ndvi is not None
            else None
        )

        for i, mask in enumerate(voted_masks or []):
            carbon, veg_class, mean_ndvi = \
                self.compute_mask_carbon(mask, ndvi)

            seg = np.asarray(mask['segmentation']).astype(bool)

            if ndvi is not None and seg.shape != ndvi.shape:
                seg_for_area = cv2.resize(
                    seg.astype(np.uint8),
                    (ndvi.shape[1], ndvi.shape[0]),
                    interpolation=cv2.INTER_NEAREST
                ).astype(bool)
            else:
                seg_for_area = seg

            if ndvi is not None:
                # Only NDVI-positive pixels inside this mask count as
                # vegetation. This also prevents non-vegetation portions
                # of SAM masks from inflating Veg Area.
                mask_veg = seg_for_area & (ndvi >= 0.1)
                union_veg_mask |= mask_veg

            total_carbon += carbon
            ndvi_values.append(mean_ndvi)

            area_m2 = float(mask.get(
                'area_m2',
                seg.sum() * (self.cfg.SPATIAL_RESOLUTION ** 2)
            ))

            breakdown.append({
                'mask_id': i,
                'channel': mask.get('channel_source', 'unknown'),
                'area_m2': round(area_m2, 2),
                'area_ha': round(area_m2 / 10000.0, 4),
                'mean_ndvi': round(mean_ndvi, 4),
                'veg_class': veg_class,
                'carbon_score': round(carbon, 4),
                'roundness': round(mask.get('roundness', 0), 4),
                'eccentricity': round(mask.get('eccentricity', 1), 4),
            })

        # --------------------------------------------------------
        # Vegetation area:
        #   masks available -> union of NDVI vegetation inside masks
        #   no masks         -> full-image NDVI vegetation area
        # --------------------------------------------------------
        if union_veg_mask is not None and union_veg_mask.any():
            pixel_area_m2 = self.cfg.SPATIAL_RESOLUTION ** 2
            total_veg_area_m2 = float(
                union_veg_mask.sum() * pixel_area_m2
            )
            veg_coverage_pct = float(
                union_veg_mask.mean() * 100.0
            )
            area_source = 'voted_masks + NDVI'
        else:
            total_veg_area_m2 = ndvi_veg_area_m2
            veg_coverage_pct = ndvi_veg_pct
            area_source = 'full NDVI fallback'

            # Do not report zero carbon solely because SAM voting produced
            # no final masks. Use the real Sentinel-2 NDVI vegetation map
            # with the same configured density/rate classification.
            if ndvi is not None and ndvi.size:
                veg_pixels = ndvi[ndvi >= 0.1]
                if veg_pixels.size:
                    fallback_mean_ndvi = float(veg_pixels.mean())
                    fallback_class, fallback_rate = self.classify_vegetation_density(
                        fallback_mean_ndvi
                    )
                    total_carbon = float(
                        fallback_rate * total_veg_area_m2 / 10000.0
                    )
                    breakdown.append({
                        'mask_id': 'ndvi_fallback',
                        'channel': 'ndvi',
                        'area_m2': round(total_veg_area_m2, 2),
                        'area_ha': round(total_veg_area_m2 / 10000.0, 4),
                        'mean_ndvi': round(fallback_mean_ndvi, 4),
                        'veg_class': fallback_class,
                        'carbon_score': round(total_carbon, 4),
                        'roundness': 0.0,
                        'eccentricity': 0.0,
                    })
                    print(
                        f'   ⚡ NDVI carbon fallback: class={fallback_class}, '
                        f'rate={fallback_rate}, area={total_veg_area_m2 / 10000.0:.4f} ha'
                    )

        total_veg_area_ha = total_veg_area_m2 / 10000.0

        # Mean NDVI for health reporting.
        if ndvi_values:
            mean_ndvi_all = float(np.mean(ndvi_values))
        elif ndvi is not None and ndvi.size:
            # Use vegetation pixels where possible.
            values = ndvi[ndvi >= 0.1]
            mean_ndvi_all = float(values.mean()) if values.size else float(ndvi.mean())
        else:
            mean_ndvi_all = 0.0

        # Health score normalized from NDVI [-1, 1] → [0, 1].
        health_score = float(np.clip((mean_ndvi_all + 1.0) / 2.0, 0.0, 1.0))

        if health_score >= 0.7:
            health_label = 'EXCELLENT'
        elif health_score >= 0.5:
            health_label = 'GOOD'
        elif health_score >= 0.3:
            health_label = 'FAIR'
        else:
            health_label = 'POOR'

        return {
            'total_carbon_score': round(total_carbon, 4),
            'num_patterns': len(voted_masks or []),

            # Fixed vegetation-area outputs
            'total_veg_area_m2': round(total_veg_area_m2, 2),
            'total_veg_area_ha': round(total_veg_area_ha, 4),
            'veg_coverage_pct': round(veg_coverage_pct, 4),
            'veg_area_source': area_source,

            'ndvi_vegetation_area_m2': round(ndvi_veg_area_m2, 2),
            'ndvi_vegetation_area_ha': round(ndvi_veg_area_m2 / 10000.0, 4),

            'mean_ndvi': round(mean_ndvi_all, 4),
            'health_score': round(health_score, 4),
            'health_label': health_label,
            'breakdown': breakdown,

            # Downstream modules
            'for_fraud_detection': {
                'carbon_score': total_carbon,
                'num_patterns': len(voted_masks or []),
                'veg_area_ha': total_veg_area_ha,
            },
            'for_marketplace_ai': {
                'carbon_score': total_carbon,
                'health_score': health_score,
                'veg_area_ha': total_veg_area_ha,
            },
            'for_blockchain_nft': {
                'carbon_score': total_carbon,
                'health_label': health_label,
                'num_patterns': len(voted_masks or []),
                'veg_area_ha': total_veg_area_ha,
            },
        }


carbon_engine = CarbonEngine(cfg)
print('✅ FIXED Carbon Engine ready')
print('   Vegetation area: NDVI-based + voted-mask union + fallback')
print('   Carbon score: mask-based using configured carbon rates')




# ==============================================================
# CELL 9 — Full SILVIA Pipeline Runner(Fixed)
# Ties all steps together into one function
# ==============================================================

class SILVIAPipeline:
    """
    Complete SILVIA pipeline for one satellite image.

    Steps:
        1. Preprocessing    (resize + enhance + spectral decomposition)
        2. Mask Generation  (SAM on multiple representations)
        3. Filtering        (quality + area + roundness + eccentricity)
        4. Mask Fusion      (master-slave voting)
        5. Carbon Scoring   (NDVI-based carbon credits)
    """

    def __init__(self, cfg, preprocessor, mask_gen, filter_obj, fusion, carbon_eng):
        self.cfg          = cfg
        self.preprocessor = preprocessor
        self.mask_gen     = mask_gen
        self.filter       = filter_obj
        self.fusion       = fusion
        self.carbon       = carbon_eng

    def run(self, image_path_or_array, area_ha=1.0, verbose=True, nir_band=None):
        if verbose:
            print('\n' + '='*65)
            print('🌿 SILVIA Pipeline — Processing')
            print('='*65)

        # ══ STEP 1: Preprocessing ══════════════════════════════
        if verbose: print('\n📋 STEP 1: Preprocessing')
        image, representations, veg_indices = self.preprocessor.preprocess(
            image_path_or_array,
            apply_salt_pepper=True,
            apply_edge=False,
            apply_contrast=True,
            nir_band=nir_band
        )

        selected_reps = {}
        for ch in self.cfg.MASTER_CHANNELS + self.cfg.SLAVE_CHANNELS:
            if ch in representations:
                selected_reps[ch] = representations[ch]

        if verbose:
            print(f'   Original size : {image.shape}')
            print(f'   Selected reps : {list(selected_reps.keys())}')

        # ══ STEP 2: SAM Mask Generation ════════════════════════
        if verbose: print('\n📋 STEP 2: Mask Generation (SAM)')
        all_masks = self.mask_gen.generate_all(selected_reps, indices=veg_indices)

        # ══ STEP 3: Filtering ══════════════════════════════════
        if verbose: print('\n📋 STEP 3: Filtering')
        filtered_masks, filter_stats = self.filter.filter_all(all_masks)

        # ══ STEP 4: Mask Fusion (Voting) ═══════════════════════
        if verbose: print('\n📋 STEP 4: Mask Fusion')
        voted_masks = self.fusion.fuse(filtered_masks)
        pattern_binary, pattern_colored = self.fusion.create_pattern_image(
            voted_masks, image.shape)

        # ══ STEP 5: Carbon Scoring ═════════════════════════════
        if verbose: print('\n📋 STEP 5: Carbon Score Engine')
        ndvi_map      = veg_indices.get('ndvi', veg_indices.get('exg'))
        carbon_result = self.carbon.compute_total_carbon(
            voted_masks, ndvi_map, area_ha=area_ha)

        # ── Safety: ensure all required keys exist ──────────────
        if 'mean_ndvi' not in carbon_result:
            carbon_result['mean_ndvi'] = float(np.mean(ndvi_map)) \
                                         if ndvi_map is not None else 0.0
        if 'health_score' not in carbon_result:
            ndvi_val = carbon_result['mean_ndvi']
            carbon_result['health_score'] = float(np.clip(ndvi_val, 0, 1))
        if 'health_label' not in carbon_result:
            s = carbon_result['health_score']
            carbon_result['health_label'] = (
                'EXCELLENT' if s >= 0.7 else
                'GOOD'      if s >= 0.5 else
                'MODERATE'  if s >= 0.3 else
                'LOW'
            )
        if 'total_carbon_score' not in carbon_result:
            carbon_result['total_carbon_score'] = 0.0
        if 'num_patterns' not in carbon_result:
            carbon_result['num_patterns'] = len(voted_masks)
        if 'total_veg_area_ha' not in carbon_result:
            # Final fallback: derive vegetation area from NDVI.
            ndvi_fallback = np.asarray(ndvi_map, dtype=np.float32)
            ndvi_fallback = np.nan_to_num(
                ndvi_fallback, nan=0.0, posinf=1.0, neginf=-1.0
            )
            ndvi_fallback = np.clip(ndvi_fallback, -1.0, 1.0)
            pixel_area_m2 = self.cfg.SPATIAL_RESOLUTION ** 2
            veg_pixels = int((ndvi_fallback >= 0.1).sum())
            carbon_result['total_veg_area_m2'] = round(
                veg_pixels * pixel_area_m2, 2
            )
            carbon_result['total_veg_area_ha'] = round(
                carbon_result['total_veg_area_m2'] / 10000.0, 4
            )
            carbon_result['veg_coverage_pct'] = round(
                100.0 * veg_pixels / max(ndvi_fallback.size, 1), 4
            )
            carbon_result['veg_area_source'] = 'pipeline NDVI fallback'

        # ── Compile results ─────────────────────────────────────
        result = {
            'image':            image,
            'representations':  representations,
            'veg_indices':      veg_indices,
            'pattern_binary':   pattern_binary,
            'pattern_colored':  pattern_colored,
            'all_masks':        all_masks,
            'filtered_masks':   filtered_masks,
            'voted_masks':      voted_masks,
            'filter_stats':     filter_stats,
            'num_initial_masks':sum(len(v) for v in all_masks.values()),
            'num_voted_masks':  len(voted_masks),
            'carbon':           carbon_result,
        }

        if verbose:
            print('\n' + '='*65)
            print('📊 SILVIA PIPELINE RESULTS')
            print('='*65)
            print(f'  Initial Masks       : {result["num_initial_masks"]}')
            print(f'  Voted Masks         : {result["num_voted_masks"]}')
            print(f'  Vegetation Patterns : {carbon_result["num_patterns"]}')
            print(f'  Mean NDVI           : {carbon_result["mean_ndvi"]:.4f}')
            print(f'  Health Score        : {carbon_result["health_score"]:.4f} '
                  f'({carbon_result["health_label"]})')
            print(f'  Carbon Score        : {carbon_result["total_carbon_score"]:.4f} '
                  f'tons CO2/ha/yr')
            print(f'  Veg Area            : {carbon_result["total_veg_area_ha"]:.4f} ha')
            print('='*65)

        return result


# ── Build pipeline ──
silvia_pipeline = SILVIAPipeline(
    cfg, preprocessor, mask_generator,
    silvia_filter, mask_fusion, carbon_engine
)

print('✅ Full SILVIA Pipeline ready!')
print('   Steps: Preprocess → SAM → Filter → Fuse → Carbon Score')




# ==============================================================
# MODULE 1 — REGISTERED-FARM / SENTINEL-2 AUTOMATION
# ==============================================================

import os, json, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import rasterio
from shapely.geometry import shape, mapping
from shapely.ops import transform as shapely_transform
from pyproj import Transformer


class ObservationConfig:
    FARM_API = os.getenv("GREENLEDGER_FARM_API", "http://127.0.0.1:8000").rstrip("/")
    CDSE_TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    CDSE_CATALOG_URL = "https://sh.dataspace.copernicus.eu/catalog/v1/search"
    CDSE_PROCESS_URL = "https://sh.dataspace.copernicus.eu/process/v1"
    COLLECTION = "sentinel-2-l2a"
    MAX_CLOUD_COVER = float(os.getenv("S2_MAX_CLOUD_COVER", "20"))
    CHECK_INTERVAL_HOURS = float(os.getenv("S2_CHECK_INTERVAL_HOURS", "24"))
    RESOLUTION_M = float(os.getenv("S2_RESOLUTION_M", "10"))
    MIN_IMAGE_PIXELS = int(os.getenv("S2_MIN_IMAGE_PIXELS", "64"))
    INITIAL_LOOKBACK_DAYS = int(os.getenv("S2_INITIAL_LOOKBACK_DAYS", "90"))
    ROOT_DIR = Path(os.getenv("GREENLEDGER_OBSERVATION_DIR", "data/observations"))
    IMAGE_DIR = ROOT_DIR / "satellite"
    STATE_FILE = ROOT_DIR / "scheduler_state.json"
    ROOT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

obs_cfg = ObservationConfig()


class FarmRegistryClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def list_farms(self):
        r = requests.get(f"{self.base_url}/api/farms", timeout=30)
        r.raise_for_status()
        return r.json().get("farms", [])

    def get_farm(self, farm_id: str):
        r = requests.get(f"{self.base_url}/api/farms/{farm_id}", timeout=30)
        r.raise_for_status()
        feature = r.json()
        if feature.get("type") != "Feature":
            raise ValueError("Module 0 returned an invalid farm feature.")
        geom = shape(feature["geometry"])
        if geom.is_empty:
            raise ValueError("Farm boundary is empty.")
        if not geom.is_valid:
            geom = geom.buffer(0)
        if geom.geom_type not in ("Polygon", "MultiPolygon"):
            raise ValueError("Farm must be a Polygon or MultiPolygon.")
        props = feature.get("properties", {})
        return {
            "farm_id": props["farm_id"],
            "farm_name": props.get("farm_name"),
            "farmer_name": props.get("farmer_name"),
            "area_ha": props.get("area_ha"),
            "geometry_wgs84": geom,
            "geometry_geojson": mapping(geom),
        }

farm_registry = FarmRegistryClient(obs_cfg.FARM_API)


class CDSEClient:
    def __init__(self):
        self.client_id = os.getenv("CDSE_CLIENT_ID")
        self.client_secret = os.getenv("CDSE_CLIENT_SECRET")
        self._token = None
        self._expires_at = 0.0

    def ready(self):
        return bool(self.client_id and self.client_secret)

    def token(self):
        if not self.ready():
            raise RuntimeError("Set CDSE_CLIENT_ID and CDSE_CLIENT_SECRET first.")
        if self._token and time.time() < self._expires_at - 60:
            return self._token
        r = requests.post(
            obs_cfg.CDSE_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=60,
        )
        r.raise_for_status()
        payload = r.json()
        self._token = payload["access_token"]
        self._expires_at = time.time() + int(payload.get("expires_in", 3600))
        return self._token

    def headers(self):
        return {"Authorization": f"Bearer {self.token()}", "Content-Type": "application/json"}

cdse = CDSEClient()


def _iso(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_state():
    if not obs_cfg.STATE_FILE.exists():
        return {}
    try:
        return json.loads(obs_cfg.STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state):
    obs_cfg.STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


class Sentinel2Automation:
    """
    Finds and downloads new Sentinel-2 L2A observations for a registered farm.
    The farm boundary comes from Module 0's database-backed API.
    """

    def __init__(self, registry: FarmRegistryClient, auth: CDSEClient):
        self.registry = registry
        self.auth = auth

    def search_newest(self, farm, after_dt=None):
        """Find the newest Sentinel-2 L2A scene for comparison.

        We intentionally search the whole configured look-back window on each
        manual check instead of starting after the previously selected scene.
        This allows GreenLedger to compare the newest Copernicus scene against
        the currently selected observation and keep whichever is higher quality.
        """
        end = datetime.now(timezone.utc)
        lookback_days = int(os.getenv("S2_INITIAL_LOOKBACK_DAYS", "90"))
        start = end - timedelta(days=lookback_days)

        payload = {
            "intersects": farm["geometry_geojson"],
            "collections": [obs_cfg.COLLECTION],
            "datetime": f"{_iso(start)}/{_iso(end)}",
            "limit": 100,
            "fields": {
                "include": [
                    "id",
                    "properties.datetime",
                    "properties.eo:cloud_cover",
                    "properties.platform",
                ]
            },
        }

        r = requests.post(
            obs_cfg.CDSE_CATALOG_URL,
            headers=self.auth.headers(),
            json=payload,
            timeout=60,
        )
        r.raise_for_status()

        features = [
            f for f in r.json().get("features", [])
            if f.get("properties", {}).get("datetime")
        ]
        features.sort(
            key=lambda f: f["properties"]["datetime"],
            reverse=True,
        )

        print(f"🔎 Sentinel-2 candidates found: {len(features)}")
        for candidate in features[:10]:
            props = candidate.get("properties", {})
            cc = props.get("eo:cloud_cover")
            cc_text = f"{float(cc):.2f}%" if isinstance(cc, (int, float)) else "unknown"
            print(f"   • {props['datetime']} | cloud={cc_text} | {candidate.get('id', '')}")

        if not features:
            print(
                f"⚠️ No Sentinel-2 L2A candidates intersected the farm "
                f"during {_iso(start)} → {_iso(end)}."
            )
            return None

        # Do not blindly choose the newest image.
        # First keep only scenes that satisfy the configured cloud threshold,
        # then choose the clearest usable scene. Newest breaks ties.
        usable = []
        for candidate in features:
            props = candidate.get("properties", {})
            cloud = props.get("eo:cloud_cover")
            if isinstance(cloud, (int, float)) and float(cloud) <= obs_cfg.MAX_CLOUD_COVER:
                usable.append(candidate)

        print(
            f"✅ Usable after cloud filter (<= {obs_cfg.MAX_CLOUD_COVER:.1f}%): "
            f"{len(usable)}"
        )

        if not usable:
            best = min(
                features,
                key=lambda x: x.get("properties", {}).get(
                    "eo:cloud_cover", float("inf")
                )
            )
            best_cloud = best.get("properties", {}).get("eo:cloud_cover")
            print(
                f"⚠️ No candidate is within the cloud threshold. "
                f"Clearest available scene is "
                f"{best_cloud:.2f}% cloudy."
                if isinstance(best_cloud, (int, float))
                else "⚠️ No candidate is within the cloud threshold."
            )
            return None

        # Lowest cloud cover is considered better.
        # If cloud cover is equal, take the newer observation.
        chosen = min(
            usable,
            key=lambda x: (
                float(x["properties"]["eo:cloud_cover"]),
                -datetime.fromisoformat(
                    x["properties"]["datetime"].replace("Z", "+00:00")
                ).timestamp(),
            ),
        )

        props = chosen.get("properties", {})
        cloud = props.get("eo:cloud_cover")

        print(
            f"🛰️ Selected best usable Sentinel-2 observation: "
            f"{props['datetime']} | cloud={float(cloud):.2f}%"
        )
        print(
            "   Selection rule: lowest cloud cover first; "
            "newest scene breaks ties."
        )

        return chosen

    @staticmethod
    def _utm_epsg(geom):
        lon = geom.centroid.x
        lat = geom.centroid.y
        zone = int((lon + 180) // 6) + 1
        return (32600 if lat >= 0 else 32700) + zone

    def download_bands(self, farm, scene):
        scene_dt = scene["properties"]["datetime"]
        scene_date = scene_dt[:10]
        epsg = self._utm_epsg(farm["geometry_wgs84"])
        transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
        geom_utm = shapely_transform(transformer.transform, farm["geometry_wgs84"])
        minx, miny, maxx, maxy = geom_utm.bounds
        pad = obs_cfg.RESOLUTION_M
        minx -= pad; miny -= pad; maxx += pad; maxy += pad

        # The farm can be much smaller than the native Sentinel-2 scene.
        # Request a minimum raster size so SAM has enough spatial context.
        # Keep the native 10 m ground sampling distance; we enlarge the AOI
        # around its centre rather than upscaling the pixels afterwards.
        min_size_px = int(os.getenv("S2_MIN_IMAGE_PIXELS", "64"))
        min_width_m = min_size_px * obs_cfg.RESOLUTION_M
        min_height_m = min_size_px * obs_cfg.RESOLUTION_M

        cx = (minx + maxx) / 2.0
        cy = (miny + maxy) / 2.0
        half_w = max((maxx - minx) / 2.0, min_width_m / 2.0)
        half_h = max((maxy - miny) / 2.0, min_height_m / 2.0)
        minx, maxx = cx - half_w, cx + half_w
        miny, maxy = cy - half_h, cy + half_h

        width = max(min_size_px, int(np.ceil((maxx - minx) / obs_cfg.RESOLUTION_M)))
        height = max(min_size_px, int(np.ceil((maxy - miny) / obs_cfg.RESOLUTION_M)))

        print(
            f"📐 Retrieval raster: {width} × {height} pixels "
            f"at {obs_cfg.RESOLUTION_M:.0f} m resolution"
        )

        evalscript = """
        //VERSION=3
        function setup() {
          return { input: ["B02", "B03", "B04", "B08", "SCL"],
                   output: { bands: 5, sampleType: "FLOAT32" } };
        }
        function evaluatePixel(sample) {
          return [sample.B02, sample.B03, sample.B04, sample.B08, sample.SCL];
        }
        """
        scene_from = datetime.fromisoformat(scene_dt.replace("Z", "+00:00"))
        scene_to = scene_from + timedelta(seconds=2)
        payload = {
            "input": {
                "bounds": {
                    "bbox": [minx, miny, maxx, maxy],
                    "properties": {"crs": f"http://www.opengis.net/def/crs/EPSG/0/{epsg}"},
                    "geometry": mapping(geom_utm),
                },
                "data": [{
                    "type": obs_cfg.COLLECTION,
                    "dataFilter": {
                        "timeRange": {"from": _iso(scene_from), "to": _iso(scene_to)},
                        "maxCloudCoverage": obs_cfg.MAX_CLOUD_COVER,
                        "mosaickingOrder": "leastCC",
                    },
                }],
            },
            "output": {
                "width": width, "height": height,
                "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}],
            },
            "evalscript": evalscript,
        }
        r = requests.post(
            obs_cfg.CDSE_PROCESS_URL,
            headers={**self.auth.headers(), "Accept": "image/tiff"},
            json=payload,
            timeout=300,
        )
        r.raise_for_status()
        outdir = obs_cfg.IMAGE_DIR / farm["farm_id"]
        outdir.mkdir(parents=True, exist_ok=True)
        outpath = outdir / f"{farm['farm_id']}_{scene_date}_{epsg}.tif"
        outpath.write_bytes(r.content)
        return outpath


s2 = Sentinel2Automation(farm_registry, cdse)


def load_sentinel_observation(path):
    with rasterio.open(path) as src:
        data = src.read().astype(np.float32)
    if data.shape[0] < 5:
        # Backward-compatible local 4-band test image.
        if data.shape[0] != 4:
            raise ValueError("Expected 4 bands B02/B03/B04/B08 or 5 bands including SCL.")
        blue, green, red, nir = data
        scl = None
    else:
        blue, green, red, nir, scl = data[:5]
    blue, green, red, nir = [np.clip(x, 0, 1) for x in (blue, green, red, nir)]
    rgb = np.stack([red, green, blue], axis=-1)
    rgb8 = (np.clip(rgb * 3.5, 0, 1) * 255).astype(np.uint8)
    return rgb8, {"blue":blue, "green":green, "red":red, "nir":nir}, scl


def process_observation(farm, scene, image_path, crop_name=None):
    rgb, bands, scl = load_sentinel_observation(image_path)
    H, W = rgb.shape[:2]
    image_area_ha = H * W * (obs_cfg.RESOLUTION_M ** 2) / 10000.0

    # Existing SAM/SILVIA inference; no retraining.
    pipeline_result = silvia_pipeline.run(
        rgb,
        area_ha=farm["area_ha"] or image_area_ha,
        verbose=True,
        nir_band=bands["nir"],
    )

    # Robust vegetation-area calculation based on real NIR/Red NDVI.
    ndvi = (bands["nir"] - bands["red"]) / (bands["nir"] + bands["red"] + 1e-8)
    ndvi = np.clip(np.nan_to_num(ndvi, nan=0.0, posinf=1.0, neginf=-1.0), -1, 1)

    valid = np.ones_like(ndvi, dtype=bool)
    if scl is not None:
        # Sentinel-2 SCL: 8/9/10 = cloud probabilities / cirrus; 3 = cloud shadow; 11 = snow/ice.
        valid &= ~np.isin(scl.astype(np.int16), [3, 8, 9, 10, 11])

    veg = (ndvi >= 0.1) & valid
    pixel_area_m2 = obs_cfg.RESOLUTION_M ** 2
    veg_area_m2 = float(veg.sum() * pixel_area_m2)
    veg_area_ha = veg_area_m2 / 10000.0
    coverage = float(veg.sum() / max(valid.sum(), 1) * 100.0)
    veg_ndvi = ndvi[veg]
    mean_ndvi = float(veg_ndvi.mean()) if veg_ndvi.size else 0.0
    health = "EXCELLENT" if mean_ndvi >= .6 else "GOOD" if mean_ndvi >= .3 else "FAIR" if mean_ndvi >= .1 else "POOR"

    carbon_score = float(pipeline_result["carbon"].get("total_carbon_score", 0.0))
    scene_dt = scene["properties"]["datetime"]
    cloud = scene.get("properties", {}).get("eo:cloud_cover")
    observation = {
        "farm_id": farm["farm_id"],
        "farm_name": farm.get("farm_name"),
        "farmer_name": farm.get("farmer_name"),
        "farm_area_ha": farm.get("area_ha"),
        "observation_date": scene_dt,
        "crop": crop_name,
        "image_path": str(image_path),
        "satellite_collection": obs_cfg.COLLECTION,
        "scene_id": scene.get("id"),
        "cloud_cover_pct": cloud,
        "mean_ndvi": mean_ndvi,
        "vegetation_area_m2": veg_area_m2,
        "vegetation_area_ha": veg_area_ha,
        "vegetation_coverage_pct": coverage,
        "vegetation_health": health,
        "initial_masks": int(pipeline_result["num_initial_masks"]),
        "voted_masks": int(pipeline_result["num_voted_masks"]),
        "carbon_score": carbon_score,
        "carbon_unit": "tons CO2/ha/yr",
        "area_source": "NDVI >= 0.1",
    }

    # Persist observation through Module 0 DB API.
    r = requests.post(f"{obs_cfg.FARM_API}/api/observations", json=observation, timeout=60)
    r.raise_for_status()
    print("✅ Observation stored in Module 0 database")
    return observation



def _calculate_observation_quality(image_path, scene):
    """Return a comparable quality score for a downloaded observation.

    Score = 60% cloud-clear score + 40% valid-SCL-pixel score.
    Higher is better. This is an engineering quality score, not a carbon-credit
    certification metric.
    """
    cloud = scene.get("properties", {}).get("eo:cloud_cover")
    cloud_clear_score = 1.0 - (float(cloud) / 100.0) if isinstance(cloud, (int, float)) else 0.5
    cloud_clear_score = float(np.clip(cloud_clear_score, 0.0, 1.0))

    valid_pixel_score = 0.5
    try:
        with rasterio.open(image_path) as src:
            if src.count >= 5:
                scl = src.read(5).astype(np.int16)
                valid = ~np.isin(scl, [3, 8, 9, 10, 11])
                valid_pixel_score = float(valid.mean())
    except Exception as exc:
        print(f"⚠️ Could not calculate SCL quality: {exc}")

    quality = 0.60 * cloud_clear_score + 0.40 * valid_pixel_score
    return {
        "quality_score": round(float(quality), 6),
        "cloud_cover_pct": float(cloud) if isinstance(cloud, (int, float)) else None,
        "valid_pixel_pct": round(valid_pixel_score * 100.0, 4),
    }


def _get_existing_quality(state_entry):
    """Get stored quality score, or derive it from the existing TIFF when possible."""
    if not state_entry:
        return None

    stored = state_entry.get("quality_score")
    if stored is not None:
        try:
            return float(stored)
        except (TypeError, ValueError):
            pass

    old_path = state_entry.get("last_image_path")
    old_scene_id = state_entry.get("last_scene_id")
    if not old_path or not Path(old_path).exists():
        return None

    old_scene = {
        "id": old_scene_id,
        "properties": {
            "datetime": state_entry.get("last_observation_datetime"),
            "eo:cloud_cover": state_entry.get("last_cloud_cover_pct"),
        },
    }
    try:
        return _calculate_observation_quality(Path(old_path), old_scene)["quality_score"]
    except Exception:
        return None

def check_farm(farm_id: str, crop_name=None):
    """Check a farm, compare the newest scene with the selected one, and keep the better image."""
    farm = farm_registry.get_farm(farm_id)
    state = _load_state()
    current = state.get(farm_id, {})

    scene = s2.search_newest(farm)
    if scene is None:
        print(f"ℹ️ No Sentinel-2 candidate available for {farm_id}.")
        return None

    new_scene_id = scene.get("id")
    old_scene_id = current.get("last_scene_id")

    # Avoid downloading/processing the same Copernicus scene repeatedly.
    if new_scene_id and new_scene_id == old_scene_id:
        print(f"✅ Newest Copernicus scene is already selected: {new_scene_id}")
        print("   No new processing required.")
        return None

    print("⬇️ Downloading newest Copernicus candidate for quality comparison...")
    new_image_path = s2.download_bands(farm, scene)
    new_quality = _calculate_observation_quality(new_image_path, scene)
    old_quality = _get_existing_quality(current)

    print("🔎 Observation quality comparison:")
    print(
        f"   NEW: cloud={new_quality['cloud_cover_pct']}% | "
        f"valid_pixels={new_quality['valid_pixel_pct']:.2f}% | "
        f"quality={new_quality['quality_score']:.4f}"
    )
    if old_quality is not None:
        print(f"   OLD: scene={old_scene_id} | quality={old_quality:.4f}")
    else:
        print("   OLD: no quality score available (first usable observation)")

    tie_margin = float(os.getenv("S2_QUALITY_TIE_MARGIN", "0.05"))

    if old_quality is not None and new_quality["quality_score"] < old_quality - tie_margin:
        print("↩️ Existing observation is better. Keeping the existing selected image.")
        try:
            new_image_path.unlink(missing_ok=True)
        except Exception:
            pass
        return None

    if old_quality is None:
        print("✅ No existing comparable observation. Selecting the newest candidate.")
    elif abs(new_quality["quality_score"] - old_quality) <= tie_margin:
        print(f"✅ Quality is within tie margin ({tie_margin:.2f}). Newer image wins.")
    else:
        print("✅ Newest candidate has better quality. Selecting it.")

    # Only the selected image enters the expensive SAM/SILVIA pipeline.
    result = process_observation(farm, scene, new_image_path, crop_name=crop_name)
    scene_dt = datetime.fromisoformat(scene["properties"]["datetime"].replace("Z", "+00:00"))

    state[farm_id] = {
        "last_observation_datetime": scene_dt.isoformat(),
        "last_scene_id": scene.get("id"),
        "last_image_path": str(new_image_path),
        "last_carbon_score": result["carbon_score"],
        "last_cloud_cover_pct": new_quality["cloud_cover_pct"],
        "last_valid_pixel_pct": new_quality["valid_pixel_pct"],
        "quality_score": new_quality["quality_score"],
    }
    _save_state(state)
    return result


def run_all_registered_farms_once(crop_name=None):
    farms = farm_registry.list_farms()
    results = []
    for feature in farms:
        farm_id = feature["properties"]["farm_id"]
        try:
            result = check_farm(farm_id, crop_name=crop_name)
            if result:
                results.append(result)
        except Exception as exc:
            print(f"❌ {farm_id}: {type(exc).__name__}: {exc}")
    print(f"✅ Cycle complete. New observations processed: {len(results)}")
    return results


def run_scheduler(crop_name=None):
    print("🔄 GreenLedger Module 1 scheduler started")
    print(f"   Farm API: {obs_cfg.FARM_API}")
    print(f"   Check interval: {obs_cfg.CHECK_INTERVAL_HOURS} hours")
    while True:
        try:
            run_all_registered_farms_once(crop_name=crop_name)
        except Exception as exc:
            print(f"❌ Scheduler cycle error: {type(exc).__name__}: {exc}")
        time.sleep(obs_cfg.CHECK_INTERVAL_HOURS * 3600)


print("✅ Module 1 automation layer ready")
print("   Note: Module 1 reads farms from Module 0's database-backed API.")
print("   Note: Copernicus OAuth tokens are obtained automatically when needed.")
print("   Note: SAM is loaded once and reused for inference; no retraining per observation.")
print("   Note: Each farm check compares the newest scene with the selected observation and keeps the better-quality image.")

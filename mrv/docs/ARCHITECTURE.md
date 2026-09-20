# GreenLedger Standards-Aligned Architecture

Existing components are preserved:
- Module 0: polygon-based farm/project registration and database.
- Module 1: Sentinel-2 + SAM/SILVIA observation pipeline.

Downstream modules added here:
1. Spatial SOC Engine
2. Methodology Registry
3. Baseline & Additionality Engine
4. GHG/Leakage/Permanence Engine
5. Uncertainty & QA/QC
6. Evidence/Audit Ledger
7. MRV report generator

## Core distinction
The ML model returns a prediction. The MRV engine separately transforms eligible inputs into a methodology-specific estimate. Neither component independently issues an official carbon credit.

## Spatial rule
Polygon is the primary land unit. Centroid is only a spatial reference for nearby observations, distance and spatial context. It must not replace polygon clipping, polygon area or farm geometry.

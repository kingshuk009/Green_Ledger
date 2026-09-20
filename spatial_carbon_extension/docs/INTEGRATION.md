# Integration

Do not replace Module 0 or Module 1.

Module 0 supplies the registered GeoJSON polygon and owner/project/management data.
Module 1 supplies polygon-level satellite statistics.

Recommended flow:
1. Load farm polygon.
2. Calculate polygon area.
3. Calculate centroid only as spatial reference.
4. Load latest polygon-clipped Module 1 features.
5. Find nearby observed soil points.
6. Create spatial neighbor features.
7. Run trained CatBoost model.
8. Return prediction plus spatial evidence and metadata.

Module 1 should eventually expose polygon-level fields such as:
ndvi_mean, ndvi_median, ndvi_std, ndvi_min, ndvi_max, veg_area_ha,
veg_coverage_pct, image_quality_score, cloud_cover, valid_pixel_pct.

# NDVI to Management Zones (Workshop)

Creates management zone polygons from Sentinel-2 NDVI rasters using k-means clustering.

## Workflow

1. Scan all Sentinel-2 NDVI scenes for a field
2. Score each by valid (non-NaN) pixel percentage within the field mask
3. Filter to June–August scenes (actively growing) with >90% coverage
4. Select the best scene
5. Nearest neighbor gap-fill of remaining NaN pixels
6. k-means clustering (k=3) on filled NDVI
7. Polygonize clusters → GeoPackage

## Output

```
fields/<field-slug>/derived/management_zones/
├── management_zones.gpkg    # Zone polygons with ndvi_mean, area_acres
├── ndvi_filled.tif          # Gap-filled NDVI raster
├── cluster_labels.tif       # Cluster label raster
└── scene_selection.json     # Chosen scene metadata
```

## Requirements

Python packages already in the pipeline venv: `rasterio`, `scikit-learn`, `scipy`, `geopandas`, `numpy`.

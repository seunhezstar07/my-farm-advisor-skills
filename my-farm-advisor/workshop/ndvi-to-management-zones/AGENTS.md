# Local Instructions

## Purpose

Workshop subskill that creates management zone polygons from Sentinel-2 NDVI rasters. For a given field, it scores available scenes by valid pixel coverage, selects the best June–August Sentinel image, fills remaining gaps via nearest neighbor interpolation, applies k-means clustering (k=3), and polygonizes the result to a GeoPackage.

## Safe edit scope

Edits should stay in this folder and its children unless the user explicitly asks for a broader skill change.

## Read nearby docs first

Read `README.md` first. Review `src/ndvi_to_zones.py` for the core processing functions.

## Runbook

From the runtime source copy after install:

```bash
export DATA_PIPELINE_DATA_ROOT=$HOME/my-farm-advisor-runtime
cd "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src"
"${DATA_PIPELINE_DATA_ROOT}/data-pipeline/.venv/bin/python" \
  scripts/create_management_zones.py \
  --grower-slug il-grower \
  --farm-slug il-grower-illinois \
  --field-id osm-1499627257
```

Output files are written to:

```
growers/<grower>/farms/<farm>/fields/<field>/derived/management_zones/
├── management_zones.gpkg
├── ndvi_filled.tif
├── cluster_labels.tif
└── scene_selection.json
```

## Local validation

Open the GeoPackage in QGIS or with `ogrinfo`. Verify three zone polygons exist with NDVI means matching low/medium/high vigour.

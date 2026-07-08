# Headlands Ring Workflow Subskill

Creates headlands ring GeoPackage outputs from a single Assignment-1 pipeline field boundary.

## Workflow

1. Read field boundary GeoJSON (EPSG:4326)
2. Copy & reproject to UTM for meter-accurate calculations
3. Compute full boundary area (m² + acres)
4. Create -21m inner buffer
5. Subtract to get headlands ring
6. Compute headlands ring area (m² + acres)
7. Convert headlands ring back to EPSG:4326
8. Write `field_boundary.gpkg` and `headlands_ring.gpkg`

## Usage

```bash
export DATA_PIPELINE_DATA_ROOT=$HOME/my-farm-advisor-runtime
cd "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src"
"${DATA_PIPELINE_DATA_ROOT}/data-pipeline/.venv/bin/python" \
  scripts/create_headlands_ring.py \
  --grower-slug il-grower \
  --farm-slug il-grower-illinois \
  --field-id osm-1525396389
```

## Output

```
growers/<grower-slug>/farms/<farm-slug>/fields/<field-id>/derived/headlands/
├── field_boundary.gpkg    # EPSG:4326
└── headlands_ring.gpkg    # EPSG:4326
```

Each GeoPackage contains `meters_squared` and `acres` columns.

## Requirements

- Python 3.10+ with `geopandas` and `shapely` (already in the pipeline venv)

# Grower Web-Map Subskill

Generates a lightweight interactive HTML web map for each grower using actual field polygon boundaries from the data pipeline.

## Features

- Reads `field_boundaries.geojson` from each farm under a grower
- Displays field polygons on an OpenStreetMap basemap (loaded from CDN)
- Click any field to see: grower, farm, field ID, area (acres), county, crop name
- Sidebar field list — click a field name to zoom to it
- Map auto-fits to show all fields
- Single self-contained HTML file (no server needed)
- Lightweight — only field geometry embedded (no imagery, no rasters)

## Usage

```bash
export DATA_PIPELINE_DATA_ROOT=$HOME/my-farm-advisor-runtime
cd "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src"
"${DATA_PIPELINE_DATA_ROOT}/data-pipeline/.venv/bin/python" \
  scripts/grower_web_map.py --grower-slug il-grower
```

## Output

```
growers/<grower-slug>/dashboards/grower_web_map.html
```

## Requirements

- Python 3.10+ with `pandas` and `geopandas` (already in the pipeline venv)
- Modern web browser to view the map

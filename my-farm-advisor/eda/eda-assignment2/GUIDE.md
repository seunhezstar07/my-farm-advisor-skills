---
name: eda-assignment2
description: Cross-grower EDA for field boundaries, CDL/cropland data, and weather comparison across IL, IA, and NE growers.
version: 1.0.0
author: Boreal Bytes
tags: [eda, cross-grower, comparison, visualization]
---

# Workflow: eda-assignment2

## Description

Generate 9 static matplotlib PNG plots comparing field boundaries, CDL crop data, and weather patterns across Illinois, Iowa, and Nebraska growers from the Assignment 2 dataset.

## Output plots

### Field Boundaries

| Plot | File | Story |
|---|---|---|
| Field area histogram | `boundaries/field_area_histogram.png` | Distribution of field sizes per state |
| Field size summary | `boundaries/field_size_summary.png` | Mean field area with error bars |
| Field area comparison | `boundaries/field_area_comparison.png` | Box plot comparison across growers |

### CDL / Cropland

| Plot | File | Story |
|---|---|---|
| Crop composition | `cdl/crop_composition_by_grower.png` | Dominant crop percentages per grower |
| Crop diversity | `cdl/crop_diversity_by_field.png` | Distinct crop count per field |
| Corn vs Soy rotation | `cdl/corn_soy_rotation_comparison.png` | Corn and soybean years comparison |

### Soil

| Plot | File | Story |
|---|---|---|
| Soil pH by state | `soil/soil_ph_by_state.png` | pH range per state — NE more alkaline, IL/IA more acidic |
| Organic matter by state | `soil/soil_om_by_state.png` | OM range per state — IL prairie soils highest |
| Soil texture comparison | `soil/soil_texture_comparison.png` | Clay/sand/silt composition per state |

### Weather

| Plot | File | Story |
|---|---|---|
| Monthly temperature | `weather/monthly_temperature_cycle.png` | Mean monthly temperature cycle per state |
| Annual precipitation | `weather/annual_precipitation.png` | Yearly total precipitation per state |
| GDD comparison | `weather/gdd_comparison.png` | Cumulative growing degree days |

## Usage

```bash
export DATA_PIPELINE_DATA_ROOT=$HOME/my-farm-advisor-runtime
cd "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src"
"${DATA_PIPELINE_DATA_ROOT}/data-pipeline/.venv/bin/python" \
  scripts/run_eda.py
```

## Filtering options

```bash
# Specific growers
python scripts/run_eda.py --growers il-grower,ne-grower

# Specific categories
python scripts/run_eda.py --categories boundaries,weather
```

## Data Dictionary

### Output files

| File | Content | Source |
|---|---|---|
| `plots/boundaries/field_area_histogram.png` | Field area density by state | `field_boundaries.geojson` → `area_acres` |
| `plots/boundaries/field_size_summary.png` | Mean area ± SD per state | same |
| `plots/boundaries/field_area_comparison.png` | Box plot — field area per state | same |
| `plots/cdl/crop_composition_by_grower.png` | Crop % stacked bar | `*_cdl_*_full_composition.csv` → `crop_name`, `pct` |
| `plots/cdl/crop_diversity_by_field.png` | Distinct crop types per field | `*_crop_rotation.csv` → `crop_diversity` |
| `plots/cdl/corn_soy_rotation_comparison.png` | Mean corn vs soy years | same → `corn_years`, `soybean_years` |
| `plots/weather/monthly_temperature_cycle.png` | Monthly mean temp (°C) | `*_weather_*.csv` → `T2M`, `date` |
| `plots/weather/annual_precipitation.png` | Yearly total precip (mm) | same → `PRECTOTCORR`, `date` |
| `plots/weather/gdd_comparison.png` | Cumulative GDD (base 10°C) | same → `T2M_MAX`, `T2M_MIN` |
| `plots/geospatial/grower_overview_map.png` | Field centroids on state map | `field_boundaries.geojson` → centroid |
| `report/assignment2_eda_report.html` | Self-contained HTML with all figures | all of the above |

### Key input columns

| Column | Source | Type | Used in |
|---|---|---|---|
| `area_acres` | `field_boundaries.geojson` | float | boundary plots |
| `crop_name` | `*_cdl_*_full_composition.csv` | str | crop composition |
| `pct` | same | float | crop composition |
| `crop_diversity` | `*_crop_rotation.csv` | int | crop diversity |
| `corn_years`, `soybean_years` | same | int | rotation comparison |
| `T2M` | `*_weather_*.csv` | float (°C) | temperature |
| `T2M_MAX`, `T2M_MIN` | same | float (°C) | GDD |
| `PRECTOTCORR` | same | float (mm) | precipitation |
| `date` | same | date | all weather plots |
| `avg_ph` | `*_ssurgo_summary.csv` | float | soil pH plot |
| `avg_om_pct` | same | float (%) | soil OM plot |
| `avg_clay_pct`, `avg_sand_pct` | same | float (%) | soil texture plot |

## Requirements

- Python 3.10+ with `pandas`, `geopandas`, `matplotlib` (already in the pipeline venv)

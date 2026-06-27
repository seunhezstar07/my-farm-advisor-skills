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

## Requirements

- Python 3.10+ with `pandas`, `geopandas`, `matplotlib` (already in the pipeline venv)

# Local Instructions

## Purpose

This subskill creates headlands ring GeoPackage outputs from a single Assignment-1 pipeline field boundary. It reads EPSG:4326 field boundaries, reprojects to UTM for accurate area calculations, creates a -21m inner buffer, computes the headlands ring, and writes two GeoPackage files.

## Safe edit scope

Edits should stay in this folder and its children unless the user explicitly asks for a broader skill change. Do not change parent `README.md`, `AGENTS.md`, sibling workflows, or root policy from a subskill task unless explicitly requested.

## Read nearby docs first

Read `README.md` first. Review `src/create_headlands_gpkg.py` for the core processing logic.

## Runbook

From the runtime source copy after install:

```bash
export DATA_PIPELINE_DATA_ROOT=$HOME/my-farm-advisor-runtime
cd "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src"
"${DATA_PIPELINE_DATA_ROOT}/data-pipeline/.venv/bin/python" \
  scripts/create_headlands_ring.py \
  --grower-slug il-grower \
  --farm-slug il-grower-illinois \
  --field-id osm-1525396389
```

Output files are written to:

```
growers/<grower-slug>/farms/<farm-slug>/fields/<field-id>/derived/headlands/
├── field_boundary.gpkg    # EPSG:4326, with meters_squared + acres
└── headlands_ring.gpkg    # EPSG:4326, with meters_squared + acres
```

## Local validation

Open the output GeoPackages with `ogrinfo` or QGIS. Verify the field boundary and headlands ring are both EPSG:4326 and contain `meters_squared` and `acres` columns.

## Local-delta-only reminder

This nested AGENTS.md only records instructions that differ from the parent or root files. Do not duplicate root-wide asset, vendor, or validation policy here except this pointer to `../../../AGENTS.md`.

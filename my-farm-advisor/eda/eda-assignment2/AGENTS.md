# Local Instructions

## Purpose

This subskill generates cross-grower EDA visualizations comparing field boundaries, CDL/cropland data, and weather patterns across IL, IA, and NE growers. All plots are static matplotlib PNGs for later assembly into a report.

## Safe edit scope

Edits should stay in this folder and its children unless the user explicitly asks for a broader skill change. Do not change parent `SKILL.md`, sibling workflows, or root policy from a subskill task unless explicitly requested.

## Read nearby docs first

Read `GUIDE.md` first. For CLI usage, see `data-pipeline/src/scripts/run_eda.py`. For the existing data structure, review `../../data-pipeline/README.md`.

## Runbook

From the runtime source copy:

```bash
export DATA_PIPELINE_DATA_ROOT=$HOME/my-farm-advisor-runtime
cd "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src"
"${DATA_PIPELINE_DATA_ROOT}/data-pipeline/.venv/bin/python" \
  scripts/run_eda.py
```

Output plots are written to:

```
growers/eda/assignment2/plots/
├── boundaries/
├── cdl/
└── weather/
```

## Local validation

Open each PNG under the output directory and verify axis labels, legends, and data ranges are correct.

## Local-delta-only reminder

This nested AGENTS.md only records instructions that differ from the parent or root files. Do not duplicate root-wide asset, vendor, or validation policy here except this pointer to `../../../AGENTS.md`.

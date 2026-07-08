# Local Instructions

## Purpose

This subskill generates lightweight interactive web maps for each existing grower. Maps show field polygon boundaries from the pipeline output, display metadata on click, and include a sidebar field list for zoom navigation. Output is a self-contained HTML file requiring only a browser.

## Safe edit scope

Edits should stay in this folder and its children unless the user explicitly asks for a broader skill change. Do not change parent `README.md`, `AGENTS.md`, sibling workflows, or root policy from a subskill task unless explicitly requested.

## Read nearby docs first

Read `README.md` first, then the sibling `data-pipeline/src/scripts/grower_web_map.py` entrypoint.

## Runbook

From the runtime source copy after install:

```bash
export DATA_PIPELINE_DATA_ROOT=$HOME/my-farm-advisor-runtime
cd "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src"
"${DATA_PIPELINE_DATA_ROOT}/data-pipeline/.venv/bin/python" \
  scripts/grower_web_map.py --grower-slug il-grower
```

The output HTML is written to:

```
growers/<grower-slug>/dashboards/grower_web_map.html
```

## Local validation

Open the generated HTML in any modern browser. Verify fields render, popups show metadata on click, and the sidebar field list zooms to each field.

## Local-delta-only reminder

This nested AGENTS.md only records instructions that differ from the parent or root files. Do not duplicate root-wide asset, vendor, or validation policy here except this pointer to `../../AGENTS.md`.

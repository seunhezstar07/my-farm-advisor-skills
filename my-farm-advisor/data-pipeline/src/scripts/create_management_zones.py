#!/usr/bin/env python3
"""Create management zone polygons from Sentinel-2 NDVI for a single field.

Usage:
    python scripts/create_management_zones.py \
        --grower-slug il-grower \
        --farm-slug il-grower-illinois \
        --field-id osm-1499627257

Output:
    growers/<grower>/farms/<farm>/fields/<field>/derived/management_zones/
    ├── management_zones.gpkg
    ├── ndvi_filled.tif
    ├── cluster_labels.tif
    └── scene_selection.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _find_skill_root(runtime_base: Path) -> Path:
    locator_path = runtime_base / ".my-farm-advisor-source.json"
    if locator_path.exists():
        try:
            info = json.loads(locator_path.read_text(encoding="utf-8"))
            root = Path(info["my_farm_advisor_skill_root"])
            if root.is_dir():
                return root
        except Exception:
            pass
    return runtime_base.parent.parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Management zones from NDVI")
    parser.add_argument("--grower-slug", required=True)
    parser.add_argument("--farm-slug", required=True)
    parser.add_argument("--field-id", required=True)
    args = parser.parse_args()

    try:
        from lib.runtime_paths import resolve_runtime_paths
    except ImportError:
        scripts_dir = Path(__file__).resolve().parent
        sys.path.insert(0, str(scripts_dir))
        sys.path.insert(0, str(scripts_dir / "lib"))
        from lib.runtime_paths import resolve_runtime_paths

    _paths = resolve_runtime_paths()
    runtime_base = _paths.runtime_base

    subskill_src = (
        runtime_base / "src" / "ndvi-to-management-zones"
        if (runtime_base / "src" / "ndvi-to-management-zones").is_dir()
        else _find_skill_root(runtime_base) / "workshop" / "ndvi-to-management-zones" / "src"
    )
    if subskill_src.is_dir():
        sys.path.insert(0, str(subskill_src))

    from ndvi_to_zones import process_field

    field_dir = (
        runtime_base / "growers" / args.grower_slug / "farms" / args.farm_slug
        / "fields" / args.field_id
    )
    if not field_dir.is_dir():
        print(f"ERROR: field directory not found: {field_dir}", file=sys.stderr)
        sys.exit(1)

    output_dir = field_dir / "derived" / "management_zones"

    result = process_field(
        grower_slug=args.grower_slug,
        farm_slug=args.farm_slug,
        field_id=args.field_id,
        field_dir=field_dir,
        output_dir=output_dir,
    )

    gpkg_rel = Path(str(output_dir / "management_zones.gpkg")).relative_to(runtime_base)
    filled_rel = Path(str(output_dir / "ndvi_filled.tif")).relative_to(runtime_base)
    label_rel = Path(str(output_dir / "cluster_labels.tif")).relative_to(runtime_base)

    print("=" * 55)
    print(f"Field:     {result['field_id']}")
    print(f"Scene:     {result['selected_scene']}  ({result['scene_date']})")
    print(f"Coverage:  {result['coverage_pct']}%  ({result['valid_pixels']}/{result['total_pixels']} pixels)")
    print(f"NDVI mean: {result['ndvi_mean']:.3f}  \u00b1 {result['ndvi_std']:.3f}")
    print(f"Zones (k={result['k_clusters']}):")
    for i, c in enumerate(result["cluster_centers_ndvi"]):
        vigour = "high" if i == 2 else ("medium" if i == 1 else "low")
        print(f"  Zone {i}: NDVI ~{c:.3f}  ({vigour} vigour)")
    print()
    print(f"GeoPackage:  {gpkg_rel}")
    print(f"Filled NDVI: {filled_rel}")
    print(f"Labels:      {label_rel}")
    print("=" * 55)


if __name__ == "__main__":
    main()

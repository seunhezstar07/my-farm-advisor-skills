#!/usr/bin/env python3
"""Create headlands ring GeoPackage files from a single field boundary.

Usage:
    python scripts/create_headlands_ring.py \
        --grower-slug il-grower \
        --farm-slug il-grower-illinois \
        --field-id osm-1525396389

Output:
    growers/<grower-slug>/farms/<farm-slug>/fields/<field-id>/derived/headlands/
    ├── field_boundary.gpkg    # EPSG:4326, with meters_squared + acres
    └── headlands_ring.gpkg    # EPSG:4326, with meters_squared + acres
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
    parser = argparse.ArgumentParser(description="Headlands ring GeoPackage generator")
    parser.add_argument("--grower-slug", required=True, help="Grower slug")
    parser.add_argument("--farm-slug", required=True, help="Farm slug")
    parser.add_argument("--field-id", required=True, help="Field ID to process")
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
    growers_root = runtime_base / "growers"
    grower_root = growers_root / args.grower_slug

    if not grower_root.is_dir():
        print(f"ERROR: grower directory not found: {grower_root}", file=sys.stderr)
        sys.exit(1)

    boundary_path = (
        grower_root / "farms" / args.farm_slug / "boundary" / "field_boundaries.geojson"
    )
    if not boundary_path.exists():
        print(f"ERROR: boundary file not found: {boundary_path}", file=sys.stderr)
        sys.exit(1)

    subskill_src = (
        runtime_base / "src" / "headlands-ring-workflow"
        if (runtime_base / "src" / "headlands-ring-workflow").is_dir()
        else _find_skill_root(runtime_base) / "field-management" / "headlands-ring-workflow" / "src"
    )
    if subskill_src.is_dir():
        sys.path.insert(0, str(subskill_src))

    from create_headlands_gpkg import process_field

    output_dir = (
        grower_root / "farms" / args.farm_slug / "fields" / args.field_id / "derived" / "headlands"
    )

    result = process_field(
        grower_slug=args.grower_slug,
        farm_slug=args.farm_slug,
        field_id=args.field_id,
        boundary_path=boundary_path,
        output_dir=output_dir,
    )

    rel_boundary = Path(result["boundary_gpkg"]).relative_to(runtime_base)
    rel_headlands = Path(result["headlands_gpkg"]).relative_to(runtime_base)

    print("=" * 50)
    print(f"Field:        {result['field_id']}")
    print(f"Grower:       {result['grower_slug']}")
    print(f"Farm:         {result['farm_slug']}")
    print(f"UTM zone:     EPSG:{result['utm_epsg']}")
    print(f"Field area:   {result['field_area_acres']:.2f} acres  ({result['field_area_sqm']:.0f} m²)")
    print(f"Headlands:    {result['headlands_area_acres']:.2f} acres  ({result['headlands_area_sqm']:.0f} m²)")
    print(f"Headlands %:  {result['headlands_pct']:.1f}%")
    print()
    print(f"Boundary:     {rel_boundary}")
    print(f"Headlands:    {rel_headlands}")
    print("=" * 50)


if __name__ == "__main__":
    main()

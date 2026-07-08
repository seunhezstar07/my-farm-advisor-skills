#!/usr/bin/env python3
"""Plot a headlands ring map for a single field boundary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from lib.runtime_paths import resolve_runtime_paths
except ImportError:
    scripts_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(scripts_dir))
    sys.path.insert(0, str(scripts_dir / "lib"))
    from lib.runtime_paths import resolve_runtime_paths


import geopandas as gpd

runtime_base = resolve_runtime_paths().runtime_base
locator_path = runtime_base / ".my-farm-advisor-source.json"
if locator_path.exists():
    info = json.loads(locator_path.read_text(encoding="utf-8"))
    skill_root = Path(info["my_farm_advisor_skill_root"])
    sys.path.insert(0, str(skill_root / "field-management" / "headlands-ring" / "src"))
from headlands_ring import create_headlands_ring, create_field_interior, plot_headlands_map  # noqa: E402


def _utm_epsg_from_point(lon: float, lat: float) -> int:
    zone = int((lon + 180) / 6) + 1
    return 32600 + zone if lat >= 0 else 32700 + zone


def main() -> None:
    parser = argparse.ArgumentParser(description="Headlands ring map plotter")
    parser.add_argument("--grower-slug", required=True)
    parser.add_argument("--farm-slug", required=True)
    parser.add_argument("--field-id", required=True)
    args = parser.parse_args()

    runtime_base = resolve_runtime_paths().runtime_base

    boundary_path = (
        runtime_base / "growers" / args.grower_slug / "farms" / args.farm_slug
        / "boundary" / "field_boundaries.geojson"
    )
    if not boundary_path.exists():
        print(f"ERROR: boundary not found: {boundary_path}", file=sys.stderr)
        sys.exit(1)

    gdf = gpd.read_file(boundary_path)
    mask = gdf["field_id"].astype(str) == args.field_id
    if not mask.any():
        print(f"ERROR: field '{args.field_id}' not found", file=sys.stderr)
        sys.exit(1)
    field_gdf = gdf[mask].copy().reset_index(drop=True)

    if field_gdf.crs is None:
        field_gdf = field_gdf.set_crs("EPSG:4326")

    centroid = field_gdf.unary_union.centroid
    utm_epsg = _utm_epsg_from_point(centroid.x, centroid.y)
    utm_gdf = field_gdf.to_crs(epsg=utm_epsg)

    ring_utm = create_headlands_ring(utm_gdf, width_m=21.0)
    interior_utm = create_field_interior(utm_gdf, width_m=21.0)

    ring_4326 = ring_utm.to_crs("EPSG:4326") if not ring_utm.empty else ring_utm
    interior_4326 = interior_utm.to_crs("EPSG:4326") if not interior_utm.empty else interior_utm

    output_dir = (
        runtime_base / "growers" / args.grower_slug / "farms" / args.farm_slug
        / "fields" / args.field_id / "derived" / "reports"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "headlands_map.png"

    plot_headlands_map(
        field_gdf=field_gdf,
        ring_gdf=ring_4326,
        interior_gdf=interior_4326,
        title=f"Headlands Ring — {args.field_id}",
        save_path=output_path,
    )

    rel = output_path.relative_to(runtime_base)
    print(f"Headlands map saved: {rel}")


if __name__ == "__main__":
    main()

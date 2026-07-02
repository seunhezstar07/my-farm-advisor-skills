#!/usr/bin/env python3
"""Run cross-grower EDA for field boundaries, CDL, and weather comparison.

Usage:
    python scripts/run_eda.py
    python scripts/run_eda.py --growers il-grower,ne-grower
    python scripts/run_eda.py --categories boundaries,weather
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _find_skill_root(runtime_base: Path) -> Path:
    locator_path = runtime_base / ".my-farm-advisor-source.json"
    if locator_path.exists():
        try:
            import json
            info = json.loads(locator_path.read_text(encoding="utf-8"))
            root = Path(info["my_farm_advisor_skill_root"])
            if root.is_dir():
                return root
        except Exception:
            pass
    return runtime_base.parent.parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-grower EDA plot generator")
    parser.add_argument(
        "--growers", default="il-grower,ia-grower,ne-grower",
        help="Comma-separated grower slugs (default: all three)",
    )
    parser.add_argument(
        "--categories", default="boundaries,cdl,weather,geospatial,soil",
        help="Comma-separated categories: boundaries,cdl,weather (default: all)",
    )
    parser.add_argument("--output", default=None, help="Output directory override")
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
        runtime_base / "src" / "eda-assignment2"
        if (runtime_base / "src" / "eda-assignment2").is_dir()
        else _find_skill_root(runtime_base) / "eda" / "eda-assignment2" / "src"
    )
    if subskill_src.is_dir():
        sys.path.insert(0, str(subskill_src))

    from field_cdl_weather_eda import (
        GROWER_LABELS,
        load_grower_data,
        run_all,
    )

    grower_slugs = [s.strip() for s in args.growers.split(",") if s.strip()]
    categories = [s.strip() for s in args.categories.split(",") if s.strip()]

    output_base = (
        Path(args.output)
        if args.output
        else runtime_base / "growers" / "eda" / "assignment2"
    )

    print(f"Loading data for growers: {', '.join(grower_slugs)}")
    data = load_grower_data(grower_slugs, runtime_base)
    print(f"  Boundaries: {len(data['boundaries'])} records")
    print(f"  Rotations:  {len(data['rotations'])} records")
    print(f"  Weather:    {len(data['weather'])} records")
    print(f"  Soil:       {len(data.get('soil',[]))} records")

    print(f"\nGenerating plots: {', '.join(categories)}")
    generated = run_all(data, output_base, categories=categories)

    print(f"\n{'='*50}")
    print(f"Generated {len(generated)} plot(s)")
    print(f"{'='*50}")
    for p in generated:
        rel = p.relative_to(runtime_base)
        size_kb = p.stat().st_size / 1024
        print(f"  {rel}  ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()

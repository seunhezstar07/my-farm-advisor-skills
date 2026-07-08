#!/usr/bin/env python3
"""Generate a lightweight interactive web map for a grower's fields.

Usage:
    python scripts/grower_web_map.py --grower-slug il-grower

Output:
    growers/<grower-slug>/dashboards/grower_web_map.html
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
    parser = argparse.ArgumentParser(description="Grower web-map generator")
    parser.add_argument("--grower-slug", required=True, help="Grower slug (e.g. il-grower)")
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

    subskill_src = (
        runtime_base / "src" / "grower-web-map"
        if (runtime_base / "src" / "grower-web-map").is_dir()
        else _find_skill_root(runtime_base) / "data-pipeline" / "grower-web-map" / "src"
    )
    if subskill_src.is_dir():
        sys.path.insert(0, str(subskill_src))

    from generate_grower_map import build_grower_map_html

    output_path = grower_root / "dashboards" / "grower_web_map.html"

    result = build_grower_map_html(
        grower_slug=args.grower_slug,
        grower_root=grower_root,
        output_path=output_path,
    )

    rel = result.relative_to(runtime_base)
    size_kb = result.stat().st_size / 1024
    print(f"Grower web map generated: {rel}  ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()

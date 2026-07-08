#!/usr/bin/env python3
"""View, inspect, and convert GeoTIFF files to viewable PNG images.

Usage:
    python scripts/view_tif.py shared/cdl/rasters/CDL_2025_19.tif
    python scripts/view_tif.py shared/cdl/rasters/CDL_2025_19.tif --to-png
    python scripts/view_tif.py shared/cdl/rasters/CDL_2025_19.tif --serve
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

try:
    from lib.runtime_paths import resolve_runtime_paths
except ImportError:
    scripts_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(scripts_dir))
    sys.path.insert(0, str(scripts_dir / "lib"))
    from lib.runtime_paths import resolve_runtime_paths

import rasterio
from rasterio.plot import reshape_as_image


def _resolve_path(raw: str, runtime_base: Path) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute() or candidate.exists():
        return candidate
    return runtime_base / candidate


def _band_label(band_idx: int, description: str | None, tags: dict) -> str:
    label = tags.get("long_name", description or f"Band {band_idx + 1}")
    label = tags.get("NAME", label)
    return str(label)


def inspect_tif(path: Path) -> dict:
    with rasterio.open(path) as src:
        info = {
            "path": str(path),
            "file_size_kb": path.stat().st_size / 1024,
            "driver": src.driver,
            "width": src.width,
            "height": src.height,
            "count": src.count,
            "dtypes": [src.dtypes[i] for i in range(src.count)],
            "crs": str(src.crs) if src.crs else "None",
            "nodata": src.nodata,
            "bounds": {"left": src.bounds.left, "bottom": src.bounds.bottom,
                       "right": src.bounds.right, "top": src.bounds.top},
            "res": (src.res[0], src.res[1]),
            "bands": [],
        }
        for i in range(1, src.count + 1):
            band = src.read(i)
            valid = band[band != src.nodata] if src.nodata is not None else band
            band_info = {
                "index": i,
                "dtype": src.dtypes[i - 1],
                "description": src.descriptions[i - 1] if src.descriptions else None,
                "tags": src.tags(i),
                "min": float(valid.min()) if valid.size > 0 else None,
                "max": float(valid.max()) if valid.size > 0 else None,
                "mean": float(valid.mean()) if valid.size > 0 else None,
            }
            info["bands"].append(band_info)
        return info


def print_info(info: dict) -> None:
    print(f"File:       {info['path']}")
    print(f"Size:       {info['file_size_kb']:.0f} KB")
    print(f"Driver:     {info['driver']}")
    print(f"Dimensions: {info['width']} x {info['height']}  ({info['count']} band(s))")
    print(f"Dtypes:     {', '.join(info['dtypes'])}")
    print(f"CRS:        {info['crs']}")
    print(f"NoData:     {info['nodata']}")
    b = info['bounds']
    print(f"Bounds:     {b['left']:.4f}, {b['bottom']:.4f}, {b['right']:.4f}, {b['top']:.4f}")
    print(f"Resolution: {info['res'][0]:.4f}, {info['res'][1]:.4f}")
    print(f"\nBands ({len(info['bands'])}):")
    for band in info['bands']:
        label = _band_label(band['index'], band['description'], band['tags'])
        print(f"  [{band['index']}] {label}")
        print(f"      dtype={band['dtype']}, "
              f"min={band['min']:.4f}, max={band['max']:.4f}, "
              f"mean={band['mean']:.4f}" if band['min'] is not None else "      (empty)")
    print()


MAX_RENDER_PIXELS = 5000


def _downsample_shape(src: rasterio.DatasetReader) -> tuple[int, int] | None:
    """Return out_shape to downsample if dimensions exceed MAX_RENDER_PIXELS."""
    h, w = src.height, src.width
    if h <= MAX_RENDER_PIXELS and w <= MAX_RENDER_PIXELS:
        return None
    scale = min(MAX_RENDER_PIXELS / h, MAX_RENDER_PIXELS / w, 1.0)
    return (max(1, int(h * scale)), max(1, int(w * scale)))


def convert_to_png(path: Path, output_path: Path | None = None, dpi: int = 150) -> Path:
    if output_path is None:
        output_path = path.with_suffix(".png")

    with rasterio.open(path) as src:
        nodata = src.nodata
        band_count = src.count
        description = src.descriptions[0] if src.descriptions else None
        tags = src.tags(1)
        basename = path.name
        out_shape = _downsample_shape(src)
        if out_shape:
            data = src.read(out_shape=out_shape)
            ds_factor = round(src.height / out_shape[0])
            print(f"  Downsampled {ds_factor}x ({src.width}x{src.height} -> {out_shape[1]}x{out_shape[0]})")
        else:
            data = src.read()

    fig, axes = plt.subplots(1, 1, figsize=(10, 8))
    ax = axes

    if band_count >= 3:
        rgb = reshape_as_image(data[:3].astype(np.float32))
        for i in range(3):
            band = data[i].astype(np.float32)
            if nodata is not None:
                band = np.ma.masked_equal(band, nodata)
            valid = band.compressed() if isinstance(band, np.ma.MaskedArray) else band
            p2, p98 = np.percentile(valid, [2, 98])
            rgb[:, :, i] = np.clip((rgb[:, :, i] - p2) / (p98 - p2 + 1e-10), 0, 1)
        ax.imshow(rgb)
        ax.set_title(f"RGB composite — {basename}")
    elif band_count == 1:
        band = data[0].astype(np.float32)
        if nodata is not None:
            band = np.ma.masked_equal(band, nodata)
        valid = band.compressed() if isinstance(band, np.ma.MaskedArray) else band
        if valid.size > 0:
            vmin, vmax = np.percentile(valid, [2, 98])
        else:
            vmin, vmax = 0, 1
        cmap = "RdYlGn" if "ndvi" in path.stem.lower() else "viridis"
        im = ax.imshow(band, cmap=cmap, vmin=vmin, vmax=vmax)
        plt.colorbar(im, ax=ax, shrink=0.7)
        label = _band_label(0, description, tags)
        ax.set_title(f"{label} — {basename}")
    else:
        ax.text(0.5, 0.5, f"{band_count}-band data\nUse --bands to select", ha="center", va="center", transform=ax.transAxes)

    ax.set_axis_off()
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)

    size_kb = output_path.stat().st_size / 1024
    print(f"Saved: {output_path}  ({size_kb:.0f} KB)")
    return output_path


def serve_file(path: Path, runtime_base: Path) -> None:
    parent = path.parent
    filename = path.name
    png_path = path.with_suffix(".png")
    if not png_path.exists():
        convert_to_png(path)
    print(f"Starting Live Server for {parent} ...")
    cmd = ["npx", "--yes", "live-server", "--port=5500", "--no-browser", str(parent)]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rel = png_path.relative_to(runtime_base) if png_path.is_relative_to(runtime_base) else png_path
    print(f"\n  Open: http://localhost:5500/{filename}")
    print(f"  PNG:  http://localhost:5500/{png_path.name}")
    print("  Press Ctrl+C to stop the server.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="GeoTIFF viewer and converter")
    parser.add_argument("tif", help="Path to .tif file (absolute or relative to runtime base)")
    parser.add_argument("--to-png", action="store_true", help="Convert to PNG and save alongside the TIFF")
    parser.add_argument("--output", "-o", help="Output PNG path (default: same name as TIFF)")
    parser.add_argument("--serve", action="store_true", help="Convert to PNG and serve via Live Server")
    parser.add_argument("--dpi", type=int, default=150, help="Output PNG DPI")
    args = parser.parse_args()

    runtime_base = resolve_runtime_paths().runtime_base
    tif_path = _resolve_path(args.tif, runtime_base)

    if not tif_path.exists():
        print(f"ERROR: file not found: {tif_path}", file=sys.stderr)
        sys.exit(1)
    if tif_path.suffix.lower() not in (".tif", ".tiff"):
        print(f"ERROR: not a TIFF file: {tif_path}", file=sys.stderr)
        sys.exit(1)

    info = inspect_tif(tif_path)
    print_info(info)

    if args.to_png or args.serve:
        output = Path(args.output) if args.output else None
        convert_to_png(tif_path, output_path=output, dpi=args.dpi)

    if args.serve:
        serve_file(tif_path, runtime_base)


if __name__ == "__main__":
    main()

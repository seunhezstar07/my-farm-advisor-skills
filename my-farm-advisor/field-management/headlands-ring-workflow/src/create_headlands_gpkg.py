from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import shapely

ACRES_PER_SQM = 0.0002471053814671653


def _utm_epsg_from_point(lon: float, lat: float) -> int:
    """Return the EPSG code for the UTM zone containing a point."""
    zone = int((lon + 180) / 6) + 1
    if lat >= 0:
        return 32600 + zone
    else:
        return 32700 + zone


def _read_single_field(
    boundary_path: Path, field_id: str
) -> gpd.GeoDataFrame:
    """Read the field_boundaries GeoJSON and return only the row matching field_id."""
    gdf = gpd.read_file(boundary_path)
    if "field_id" not in gdf.columns:
        raise ValueError(f"'field_id' column missing in {boundary_path}")
    mask = gdf["field_id"].astype(str) == field_id
    if not mask.any():
        available = gdf["field_id"].astype(str).unique().tolist()
        raise ValueError(
            f"field_id '{field_id}' not found. Available: {available}"
        )
    return gdf[mask].copy().reset_index(drop=True)


def _create_headlands_ring_utm(
    utm_gdf: gpd.GeoDataFrame, width_m: float = 21.0
) -> gpd.GeoDataFrame:
    """Create headlands ring by subtracting an inward buffer in projected space."""
    rings = []
    for geom in utm_gdf.geometry:
        inner = geom.buffer(-width_m)
        if inner.is_empty:
            # Polygon is smaller than the buffer; headlands is the whole thing
            rings.append(geom)
        else:
            rings.append(geom.difference(inner))
    valid = [geom for geom in rings if not geom.is_empty]
    return gpd.GeoDataFrame(geometry=valid, crs=utm_gdf.crs)


def process_field(
    grower_slug: str,
    farm_slug: str,
    field_id: str,
    boundary_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """
    Read a single field boundary, compute headlands ring, and write two GeoPackages.

    Returns a dict with paths and computed metrics.
    """
    # Step 1: Read field boundary in EPSG:4326
    original_gdf = _read_single_field(boundary_path, field_id)

    if original_gdf.crs is None:
        original_gdf = original_gdf.set_crs("EPSG:4326")

    # Step 2: Copy & transform to UTM working GeoDataFrame
    centroid = original_gdf.unary_union.centroid
    utm_epsg = _utm_epsg_from_point(centroid.x, centroid.y)
    utm_gdf = original_gdf.to_crs(epsg=utm_epsg)

    # Step 3: Calculate full boundary area: meters_squared + acres
    field_area_sqm = float(utm_gdf.geometry.area.sum())
    field_area_acres = field_area_sqm * ACRES_PER_SQM

    # Step 4: Write both area attributes back to original_gdf (EPSG:4326)
    original_gdf["meters_squared"] = field_area_sqm
    original_gdf["acres"] = field_area_acres

    # Step 5: Create negative 21m inner buffer
    # Step 6: Calculate difference = headlands ring
    headlands_utm = _create_headlands_ring_utm(utm_gdf, width_m=21.0)

    # Step 7: Calculate headlands ring area: meters_squared + acres
    ring_area_sqm = float(headlands_utm.geometry.area.sum()) if not headlands_utm.empty else 0.0
    ring_area_acres = ring_area_sqm * ACRES_PER_SQM
    headlands_utm["meters_squared"] = ring_area_sqm
    headlands_utm["acres"] = ring_area_acres

    # Step 8: Convert only headlands ring back to EPSG:4326
    headlands_4326 = headlands_utm.to_crs("EPSG:4326")

    # Step 9: Write 2 GeoPackage files
    output_dir.mkdir(parents=True, exist_ok=True)

    boundary_path_gpkg = output_dir / "field_boundary.gpkg"
    ring_path_gpkg = output_dir / "headlands_ring.gpkg"

    original_gdf.to_file(boundary_path_gpkg, driver="GPKG")
    headlands_4326.to_file(ring_path_gpkg, driver="GPKG")

    return {
        "field_id": field_id,
        "grower_slug": grower_slug,
        "farm_slug": farm_slug,
        "utm_epsg": utm_epsg,
        "field_area_sqm": field_area_sqm,
        "field_area_acres": field_area_acres,
        "headlands_area_sqm": ring_area_sqm,
        "headlands_area_acres": ring_area_acres,
        "headlands_pct": (ring_area_sqm / field_area_sqm * 100.0) if field_area_sqm else 0.0,
        "boundary_gpkg": str(boundary_path_gpkg),
        "headlands_gpkg": str(ring_path_gpkg),
    }

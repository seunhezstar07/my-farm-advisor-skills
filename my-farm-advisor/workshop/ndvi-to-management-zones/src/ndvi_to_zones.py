from __future__ import annotations

import json
import os
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
import rasterio.features
import rasterio.mask
from scipy.interpolate import NearestNDInterpolator
from shapely.geometry import mapping, shape
from sklearn.cluster import KMeans

ACRES_PER_SQM = 0.0002471053814671653

JUNE_AUGUST_MONTHS = {6, 7, 8}
MIN_COVERAGE = 0.90
K_CLUSTERS = 3


def scan_ndvi_scenes(sentinel_dir: Path) -> list[dict]:
    scenes: list[dict] = []
    if not sentinel_dir.is_dir():
        return scenes
    for year_dir in sorted(sentinel_dir.iterdir()):
        if not year_dir.is_dir():
            continue
        try:
            year = int(year_dir.name)
        except ValueError:
            continue
        for scene_dir in sorted(year_dir.iterdir()):
            if not scene_dir.is_dir():
                continue
            scene_name = scene_dir.name
            ndvi_path = scene_dir / f"{scene_name}_ndvi.tif"
            if not ndvi_path.exists():
                continue
            date_str = scene_name.replace("sentinel_", "")
            try:
                month = int(date_str[4:6])
            except (IndexError, ValueError):
                continue
            scenes.append({
                "path": ndvi_path,
                "scene_name": scene_name,
                "date_str": date_str,
                "year": year,
                "month": month,
                "sensor": "sentinel",
            })
    return scenes


def score_scene(ndvi_path: Path, boundary_geom) -> dict:
    with rasterio.open(ndvi_path) as src:
        out_image, out_transform = rasterio.mask.mask(
            src, [mapping(boundary_geom)], crop=True, nodata=np.nan, all_touched=True,
        )
        data = out_image[0]

        field_mask = rasterio.features.geometry_mask(
            [boundary_geom],
            out_shape=data.shape,
            transform=out_transform,
            all_touched=True,
            invert=True,
        )
        pixels_in_field = int(np.sum(field_mask))
        pixels_valid = int(np.sum(~np.isnan(data) & field_mask))
        pct = pixels_valid / pixels_in_field if pixels_in_field > 0 else 0
        valid_vals = data[~np.isnan(data) & field_mask]
        ndvi_mean = float(np.mean(valid_vals)) if len(valid_vals) > 0 else np.nan
        ndvi_std = float(np.std(valid_vals)) if len(valid_vals) > 0 else np.nan
    return {
        "total_pixels": pixels_in_field,
        "valid_pixels": pixels_valid,
        "coverage_pct": round(pct, 4),
        "ndvi_mean": ndvi_mean,
        "ndvi_std": ndvi_std,
        "data": data,
        "transform": out_transform,
        "crs": src.crs,
    }


def select_best_scene(scenes: list[dict], field_geom) -> dict | None:
    scored: list[tuple[float, dict]] = []
    for s in scenes:
        result = score_scene(s["path"], field_geom)
        result.update(s)
        coverage = result["coverage_pct"]
        month = s["month"]
        if month in JUNE_AUGUST_MONTHS and coverage >= MIN_COVERAGE:
            scored.append((coverage, result))

    if not scored:
        return None
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def nearest_neighbor_fill(raster: np.ndarray) -> np.ndarray:
    mask = np.isnan(raster)
    if not mask.any():
        return raster.copy()
    valid_y, valid_x = np.where(~mask)
    valid_vals = raster[~mask]
    interp = NearestNDInterpolator(list(zip(valid_y, valid_x)), valid_vals)
    filled = raster.copy()
    filled[mask] = interp(np.where(mask)[0], np.where(mask)[1])
    return filled


def kmeans_cluster(raster: np.ndarray, k: int = K_CLUSTERS) -> tuple[np.ndarray, np.ndarray]:
    mask = np.isnan(raster)
    if mask.all():
        return np.full_like(raster, np.nan, dtype=np.float32), np.array([])
    pixels = raster[~mask].reshape(-1, 1)
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(pixels)
    cluster_centers = km.cluster_centers_.flatten()
    order = np.argsort(cluster_centers)
    rank = np.zeros(k, dtype=int)
    rank[order] = np.arange(k)
    cluster_centers_sorted = cluster_centers[order]
    labels_sorted = rank[labels]
    result = np.full_like(raster, np.nan, dtype=np.float32)
    result[~mask] = labels_sorted
    return result, cluster_centers_sorted


def polygonize_clusters(
    cluster_array: np.ndarray,
    filled_array: np.ndarray,
    transform,
    crs,
) -> gpd.GeoDataFrame:
    mask = ~np.isnan(cluster_array)
    results: list[dict] = []
    for geom, value in rasterio.features.shapes(
        cluster_array.astype(np.int32),
        transform=transform,
        mask=mask,
    ):
        zone = int(value)
        poly = shape(geom)
        poly_mask = rasterio.features.geometry_mask(
            [poly],
            out_shape=cluster_array.shape,
            transform=transform,
            all_touched=True,
            invert=True,
        )
        zone_ndvi = filled_array[poly_mask & mask]
        area_sqm = poly.area
        if crs and crs.is_geographic:
            utm_code = _utm_epsg_from_point(poly.centroid.x, poly.centroid.y)
            try:
                import pyproj
                import shapely.ops
                project = pyproj.Transformer.from_crs(crs, f"EPSG:{utm_code}", always_xy=True).transform
                area_sqm = shapely.ops.transform(project, poly).area
            except Exception:
                pass
        results.append({
            "zone": zone,
            "ndvi_mean": float(np.mean(zone_ndvi)) if len(zone_ndvi) > 0 else 0.0,
            "ndvi_std": float(np.std(zone_ndvi)) if len(zone_ndvi) > 0 else 0.0,
            "area_acres": area_sqm * ACRES_PER_SQM,
            "geometry": poly,
        })

    if not results:
        return gpd.GeoDataFrame(columns=["zone", "ndvi_mean", "ndvi_std", "area_acres", "pct_area", "geometry"], crs=crs)

    gdf = gpd.GeoDataFrame(results, crs=crs)
    total_acres = gdf["area_acres"].sum()
    gdf["pct_area"] = (gdf["area_acres"] / total_acres * 100) if total_acres > 0 else 0.0

    dissolved = gdf.dissolve(by="zone", aggfunc={
        "ndvi_mean": "mean",
        "ndvi_std": "mean",
        "area_acres": "sum",
        "pct_area": "sum",
    }).reset_index()
    return dissolved.sort_values("zone").reset_index(drop=True)


def _utm_epsg_from_point(lon: float, lat: float) -> int:
    zone = int((lon + 180) / 6) + 1
    return 32600 + zone if lat >= 0 else 32700 + zone


def process_field(
    grower_slug: str,
    farm_slug: str,
    field_id: str,
    field_dir: Path,
    output_dir: Path,
) -> dict:
    sentinel_dir = field_dir / "satellite" / "sentinel"
    boundary_path = field_dir / "boundary" / "field_boundary.geojson"

    if not boundary_path.exists():
        raise FileNotFoundError(f"Field boundary not found: {boundary_path}")

    boundary_gdf = gpd.read_file(boundary_path)
    if boundary_gdf.crs is None:
        boundary_gdf = boundary_gdf.set_crs("EPSG:4326")
    boundary_geom = boundary_gdf.geometry.iloc[0]

    scenes = scan_ndvi_scenes(sentinel_dir)
    if not scenes:
        raise ValueError(f"No Sentinel NDVI scenes found in {sentinel_dir}")

    best = select_best_scene(scenes, boundary_geom)
    if best is None:
        details = []
        for s in scenes:
            r = score_scene(s["path"], boundary_geom)
            details.append(f"{s['scene_name']}: month={s['month']}, coverage={r['coverage_pct']:.1%}")
        raise ValueError(
            f"No June-August scene with >{MIN_COVERAGE:.0%} valid pixels found. "
            f"Scanned {len(scenes)} scenes. Details:\n" + "\n".join(details)
        )

    ndvi_data = best["data"]
    ndvi_transform = best["transform"]
    ndvi_crs = best["crs"]

    filled = nearest_neighbor_fill(ndvi_data)

    cluster_array, cluster_centers = kmeans_cluster(filled, k=K_CLUSTERS)

    zones_gdf = polygonize_clusters(cluster_array, filled, ndvi_transform, ndvi_crs)

    output_dir.mkdir(parents=True, exist_ok=True)

    gpkg_path = output_dir / "management_zones.gpkg"
    zones_gdf.to_file(gpkg_path, driver="GPKG", layer="management_zones")

    profile = {
        "driver": "GTiff",
        "height": filled.shape[0],
        "width": filled.shape[1],
        "count": 1,
        "dtype": filled.dtype,
        "crs": ndvi_crs,
        "transform": ndvi_transform,
        "compress": "lzw",
        "nodata": np.nan,
    }
    filled_path = output_dir / "ndvi_filled.tif"
    with rasterio.open(filled_path, "w", **profile) as dst:
        dst.write(filled, 1)

    label_path = output_dir / "cluster_labels.tif"
    label_profile = {**profile, "dtype": rasterio.float32, "nodata": np.nan}
    with rasterio.open(label_path, "w", **label_profile) as dst:
        dst.write(cluster_array, 1)

    scene_info = {
        "grower_slug": grower_slug,
        "farm_slug": farm_slug,
        "field_id": field_id,
        "selected_scene": best["scene_name"],
        "scene_date": best["date_str"],
        "sensor": best["sensor"],
        "valid_pixels": best["valid_pixels"],
        "total_pixels": best["total_pixels"],
        "coverage_pct": round(best["coverage_pct"] * 100, 1),
        "ndvi_mean": best["ndvi_mean"],
        "ndvi_std": best["ndvi_std"],
        "k_clusters": K_CLUSTERS,
        "cluster_centers_ndvi": [round(float(c), 4) for c in cluster_centers],
        "gap_fill_method": "nearest_neighbor",
    }
    scene_path = output_dir / "scene_selection.json"
    scene_path.write_text(json.dumps(scene_info, indent=2) + "\n", encoding="utf-8")

    return scene_info

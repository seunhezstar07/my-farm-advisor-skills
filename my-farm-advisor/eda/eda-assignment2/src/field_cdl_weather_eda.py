from __future__ import annotations

import os
from pathlib import Path

import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.use("Agg")

GDD_BASE_TEMP = 10.0

GROWER_COLORS = {
    "il-grower": "#1b9e77",
    "ia-grower": "#d95f02",
    "ne-grower": "#7570b3",
}

GROWER_LABELS = {
    "il-grower": "Illinois",
    "ia-grower": "Iowa",
    "ne-grower": "Nebraska",
}


def _prefix(farm_slug: str) -> str:
    return farm_slug.strip().replace("-", "_")


def _output_dir(base: Path, category: str) -> Path:
    p = base / "plots" / category
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_grower_data(grower_slugs: list[str], runtime_base: Path) -> dict:
    growers_root = runtime_base / "growers"
    all_boundaries: list[pd.DataFrame] = []
    all_rotations: list[pd.DataFrame] = []
    all_weather: list[pd.DataFrame] = []
    all_composition: list[pd.DataFrame] = []
    all_soil: list[pd.DataFrame] = []

    for slug in grower_slugs:
        farms_dir = growers_root / slug / "farms"
        if not farms_dir.is_dir():
            continue

        gdf_slug = slug.replace("-", " ")
        gdf_label = " ".join(w.capitalize() for w in gdf_slug.split())

        for farm_dir in sorted(farms_dir.iterdir()):
            if not farm_dir.is_dir():
                continue
            farm_slug = farm_dir.name
            prefix = _prefix(farm_slug)
            tables = farm_dir / "derived" / "tables"

            boundary_path = farm_dir / "boundary" / "field_boundaries.geojson"
            if boundary_path.exists():
                gdf = gpd.read_file(boundary_path)
                if gdf.crs is None:
                    gdf = gdf.set_crs("EPSG:4326")
                gdf = gdf.to_crs("EPSG:4326")
                for _, row in gdf.iterrows():
                    centroid = row.geometry.centroid if row.geometry is not None else None
                    all_boundaries.append(
                        {
                            "grower_slug": slug,
                            "grower_label": gdf_label,
                            "farm_slug": farm_slug,
                            "field_id": str(row.get("field_id", "")),
                            "area_acres": float(row.get("area_acres", 0)),
                            "county": str(row.get("county_name", "")),
                            "centroid_lon": float(centroid.x) if centroid is not None else None,
                            "centroid_lat": float(centroid.y) if centroid is not None else None,
                            "geometry_wkt": row.geometry.wkt if row.geometry is not None else None,
                        }
                    )

                    rotation_path = tables / f"{prefix}_crop_rotation.csv"
            if rotation_path.exists():
                df = pd.read_csv(rotation_path)
                df["grower_slug"] = slug
                df["grower_label"] = gdf_label
                df["farm_slug"] = farm_slug
                all_rotations.append(df)

            soil_summary_path = tables / f"{prefix}_ssurgo_summary.csv"
            if soil_summary_path.exists():
                sdf = pd.read_csv(soil_summary_path)
                sdf["grower_slug"] = slug
                sdf["grower_label"] = gdf_label
                sdf["farm_slug"] = farm_slug
                all_soil.append(sdf)

            weather_path = tables / f"{prefix}_weather_2021_2025.csv"
            if weather_path.exists():
                wdf = pd.read_csv(weather_path, parse_dates=["date"])
                wdf["grower_slug"] = slug
                wdf["grower_label"] = gdf_label
                wdf["farm_slug"] = farm_slug
                all_weather.append(wdf)

            composition_path = tables / f"{prefix}_cdl_2021_2025_full_composition.csv"
            if composition_path.exists():
                cdf = pd.read_csv(composition_path)
                cdf["grower_slug"] = slug
                cdf["grower_label"] = gdf_label
                cdf["farm_slug"] = farm_slug
                all_composition.append(cdf)

    return {
        "boundaries": pd.DataFrame(all_boundaries) if all_boundaries else pd.DataFrame(),
        "rotations": pd.concat(all_rotations, ignore_index=True) if all_rotations else pd.DataFrame(),
        "weather": pd.concat(all_weather, ignore_index=True) if all_weather else pd.DataFrame(),
        "composition": pd.concat(all_composition, ignore_index=True) if all_composition else pd.DataFrame(),
        "soil": pd.concat(all_soil, ignore_index=True) if all_soil else pd.DataFrame(),
    }


def _color(slug: str) -> str:
    return GROWER_COLORS.get(slug, "#333333")


def _label(slug: str) -> str:
    return GROWER_LABELS.get(slug, slug)


def plot_field_area_histogram(data: pd.DataFrame, output_base: Path) -> Path:
    out = _output_dir(output_base, "boundaries") / "field_area_histogram.png"
    fig, ax = plt.subplots(figsize=(10, 6))
    for slug in sorted(data["grower_slug"].unique()):
        subset = data[data["grower_slug"] == slug]["area_acres"]
        ax.hist(
            subset, bins=15, alpha=0.5, color=_color(slug),
            label=f'{_label(slug)} (n={len(subset)})', density=True,
        )
    ax.set_xlabel("Field area (acres)")
    ax.set_ylabel("Probability density")
    ax.set_title("Field area distribution by state")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_field_size_summary(data: pd.DataFrame, output_base: Path) -> Path:
    out = _output_dir(output_base, "boundaries") / "field_size_summary.png"
    stats = data.groupby("grower_slug")["area_acres"].agg(["mean", "std", "count"])
    fig, ax = plt.subplots(figsize=(8, 5))
    x = range(len(stats))
    labels = [_label(s) for s in stats.index]
    bars = ax.bar(
        x, stats["mean"], yerr=stats["std"], capsize=5,
        color=[_color(s) for s in stats.index], alpha=0.8,
    )
    for bar, idx in zip(bars, stats.index):
        n = int(stats.loc[idx, "count"])
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + stats.loc[idx, "std"] + 10,
                f"n={n}", ha="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Mean field area (acres)")
    ax.set_title("Mean field size by state (error bars: \u00b11 SD)")
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_field_area_comparison(data: pd.DataFrame, output_base: Path) -> Path:
    out = _output_dir(output_base, "boundaries") / "field_area_comparison.png"
    fig, ax = plt.subplots(figsize=(8, 5))
    slugs = sorted(data["grower_slug"].unique())
    groups = [data[data["grower_slug"] == s]["area_acres"] for s in slugs]
    labels = [_label(s) for s in slugs]
    colors = [_color(s) for s in slugs]
    labels_w_n = [f"{l}\n(n={len(g)})" for l, g in zip(labels, groups)]
    bp = ax.boxplot(groups, patch_artist=True)
    ax.set_xticklabels(labels_w_n)
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.6)
    ax.set_ylabel("Field area (acres)")
    ax.set_title("Field area comparison across states")
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_crop_composition(data: pd.DataFrame, output_base: Path) -> Path:
    out = _output_dir(output_base, "cdl") / "crop_composition_by_grower.png"
    grouped = data.groupby(["grower_label", "crop_name"])["pixel_count"].sum().reset_index()
    total = grouped.groupby("grower_label")["pixel_count"].sum().reset_index().rename(columns={"pixel_count": "total"})
    grouped = grouped.merge(total, on="grower_label")
    grouped["pct"] = grouped["pixel_count"] / grouped["total"] * 100

    pivot = grouped.pivot_table(
        index="grower_label", columns="crop_name", values="pct", fill_value=0,
    )
    top = pivot.sum().sort_values(ascending=False).head(6).index
    pivot = pivot[top]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = pivot.plot(kind="barh", stacked=True, ax=ax, colormap="Set2")
    ax.set_xlabel("Percent of CDL pixels (%)")
    ax.set_ylabel("")
    ax.set_title("Crop composition by state (CDL 2021\u20132025)")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(True, alpha=0.3, axis="x")
    plt.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_crop_diversity(data: pd.DataFrame, output_base: Path) -> Path:
    out = _output_dir(output_base, "cdl") / "crop_diversity_by_field.png"
    fig, ax = plt.subplots(figsize=(8, 5))
    slugs = sorted(data["grower_slug"].unique())
    groups = [data[data["grower_slug"] == s]["crop_diversity"] for s in slugs]
    labels = [_label(s) for s in slugs]
    colors = [_color(s) for s in slugs]
    labels_w_n = [f"{l}\n(n={len(g)})" for l, g in zip(labels, groups)]
    bp = ax.boxplot(groups, patch_artist=True)
    ax.set_xticklabels(labels_w_n)
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.6)
    ax.set_ylabel("Distinct crop types per field")
    ax.set_title("Crop diversity per field (CDL 2021\u20132025)")
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_corn_soy_rotation(data: pd.DataFrame, output_base: Path) -> Path:
    out = _output_dir(output_base, "cdl") / "corn_soy_rotation_comparison.png"
    stats = data.groupby("grower_label")[["corn_years", "soybean_years"]].mean().reset_index()
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(stats))
    w = 0.35
    ax.bar(x - w / 2, stats["corn_years"], w, label="Corn", color="#e7298a", alpha=0.8)
    ax.bar(x + w / 2, stats["soybean_years"], w, label="Soybeans", color="#66a61e", alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(stats["grower_label"])
    ax.set_ylabel("Mean years (out of 5)")
    ax.set_title("Mean corn and soybean years per field (2021\u20132025)")
    ax.set_ylim(0, 5.5)
    ax.axhline(2.5, color="gray", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def plot_monthly_temperature(data: pd.DataFrame, output_base: Path) -> Path:
    out = _output_dir(output_base, "weather") / "monthly_temperature_cycle.png"
    data = data.copy()
    data["month"] = data["date"].dt.month
    monthly = data.groupby(["grower_slug", "month"])["T2M"].mean().reset_index()
    fig, ax = plt.subplots(figsize=(10, 6))
    for slug in sorted(monthly["grower_slug"].unique()):
        subset = monthly[monthly["grower_slug"] == slug]
        ax.plot(
            subset["month"], subset["T2M"], marker="o", color=_color(slug),
            label=_label(slug), linewidth=2,
        )
    ax.set_xlabel("Month")
    ax.set_ylabel("Mean temperature (°C)")
    ax.set_title("Monthly mean temperature cycle (2021\u20132025)")
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(MONTH_LABELS)
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_annual_precipitation(data: pd.DataFrame, output_base: Path) -> Path:
    out = _output_dir(output_base, "weather") / "annual_precipitation.png"
    data = data.copy()
    data["year"] = data["date"].dt.year
    yearly = data.groupby(["grower_slug", "year", "field_id"])["PRECTOTCORR"].sum().reset_index()
    yearly_stats = yearly.groupby(["grower_slug", "year"])["PRECTOTCORR"].agg(["mean", "std"]).reset_index()
    fig, ax = plt.subplots(figsize=(10, 6))
    for slug in sorted(yearly_stats["grower_slug"].unique()):
        subset = yearly_stats[yearly_stats["grower_slug"] == slug]
        ax.errorbar(
            subset["year"], subset["mean"], yerr=subset["std"],
            marker="s", color=_color(slug), label=_label(slug),
            linewidth=2, capsize=4, capthick=1,
        )
    ax.set_xlabel("Year")
    ax.set_ylabel("Total precipitation (mm)")
    ax.set_title("Annual total precipitation by state (\u00b11 SD across fields)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_gdd_comparison(data: pd.DataFrame, output_base: Path) -> Path:
    out = _output_dir(output_base, "weather") / "gdd_comparison.png"
    w = data.copy()
    w["tavg"] = (w["T2M_MAX"] + w["T2M_MIN"]) / 2.0
    w["daily_gdd"] = np.maximum(0, w["tavg"] - GDD_BASE_TEMP)
    w["doy"] = w["date"].dt.dayofyear
    w["year"] = w["date"].dt.year
    w["field_year"] = w["field_id"] + "_" + w["year"].astype(str)
    w["cum_gdd"] = w.groupby(["grower_slug", "field_id", "year"])["daily_gdd"].transform("cumsum")
    avg = w.groupby(["grower_slug", "doy"])["cum_gdd"].mean().reset_index()
    fig, ax = plt.subplots(figsize=(10, 6))
    for slug in sorted(avg["grower_slug"].unique()):
        subset = avg[avg["grower_slug"] == slug]
        ax.plot(
            subset["doy"], subset["cum_gdd"], color=_color(slug),
            label=_label(slug), linewidth=2,
        )
    ax.set_xlabel("Day of year")
    ax.set_ylabel("Cumulative GDD (base 10\u00b0C)")
    ax.set_title("Mean cumulative growing degree days (2021\u20132025)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_grower_overview_map(data: pd.DataFrame, output_base: Path) -> Path:
    out = _output_dir(output_base, "geospatial") / "grower_overview_map.png"
    from shapely import wkt as shapely_wkt

    runtime_base = Path(os.environ.get("DATA_PIPELINE_DATA_ROOT", "/none")) / "data-pipeline"
    states_path = runtime_base / "shared" / "geoadmin" / "l1_states" / "states_usa.geojson"
    if not states_path.exists():
        fig, ax = plt.subplots(figsize=(10, 7))
        ax.text(0.5, 0.5, "No states boundary file available", ha="center", va="center", transform=ax.transAxes)
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return out

    states = gpd.read_file(states_path)
    focal = states[states["state_name"].isin(["Illinois", "Iowa", "Nebraska"])].copy()
    bbox = focal.total_bounds
    pad_x = (bbox[2] - bbox[0]) * 0.15
    pad_y = (bbox[3] - bbox[1]) * 0.15

    fig, ax = plt.subplots(figsize=(10, 7))
    states.boundary.plot(ax=ax, color="#cccccc", linewidth=0.5, alpha=0.7)
    focal.boundary.plot(ax=ax, color="#555555", linewidth=1.5)

    for slug in sorted(data["grower_slug"].unique()):
        subset = data[data["grower_slug"] == slug]
        valid = subset.dropna(subset=["centroid_lon", "centroid_lat"])
        ax.scatter(
            valid["centroid_lon"], valid["centroid_lat"],
            c=_color(slug), label=_label(slug), s=60, edgecolors="white",
            linewidths=0.8, zorder=5,
        )
        if not valid.empty:
            for _, row in valid.iterrows():
                ax.annotate(
                    row["field_id"], (row["centroid_lon"], row["centroid_lat"]),
                    fontsize=5, ha="center", va="bottom", alpha=0.7,
                )

    ax.set_xlim(bbox[0] - pad_x, bbox[2] + pad_x)
    ax.set_ylim(bbox[1] - pad_y, bbox[3] + pad_y)
    ax.set_title("Grower field overview \u2014 IL, IA, NE (30 fields)")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(True, alpha=0.3, linestyle=":")
    ax.legend(loc="upper right")
    plt.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_soil_ph(data: pd.DataFrame, output_base: Path) -> Path:
    out = _output_dir(output_base, "soil") / "soil_ph_by_state.png"
    fig, ax = plt.subplots(figsize=(8, 5))
    slugs = sorted(data["grower_slug"].unique())
    groups = [data[data["grower_slug"] == s]["avg_ph"].dropna() for s in slugs]
    labels = [_label(s) for s in slugs]
    colors = [_color(s) for s in slugs]
    labels_w_n = [f"{l}\n(n={len(g)})" for l, g in zip(labels, groups)]
    bp = ax.boxplot(groups, patch_artist=True)
    ax.set_xticklabels(labels_w_n)
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.6)
    ax.axhline(6.5, color="gray", linewidth=0.8, linestyle="--", alpha=0.5, label="Neutral (pH 7)")
    ax.axhline(7.0, color="gray", linewidth=0.8, linestyle=":", alpha=0.4)
    ax.set_ylabel("Soil pH")
    ax.set_title("Soil pH by state (SSURGO)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_soil_om(data: pd.DataFrame, output_base: Path) -> Path:
    out = _output_dir(output_base, "soil") / "soil_om_by_state.png"
    fig, ax = plt.subplots(figsize=(8, 5))
    slugs = sorted(data["grower_slug"].unique())
    groups = [data[data["grower_slug"] == s]["avg_om_pct"].dropna() for s in slugs]
    labels = [_label(s) for s in slugs]
    colors = [_color(s) for s in slugs]
    labels_w_n = [f"{l}\n(n={len(g)})" for l, g in zip(labels, groups)]
    bp = ax.boxplot(groups, patch_artist=True)
    ax.set_xticklabels(labels_w_n)
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.6)
    ax.set_ylabel("Organic matter (%)")
    ax.set_title("Soil organic matter by state (SSURGO)")
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_soil_texture(data: pd.DataFrame, output_base: Path) -> Path:
    out = _output_dir(output_base, "soil") / "soil_texture_comparison.png"
    tex = data.copy()
    tex["avg_silt_pct"] = 100.0 - tex["avg_clay_pct"] - tex["avg_sand_pct"]
    stats = tex.groupby("grower_label")[["avg_clay_pct", "avg_sand_pct", "avg_silt_pct"]].mean().reset_index()
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(stats))
    w = 0.5
    ax.bar(x, stats["avg_sand_pct"], w, label="Sand", color="#e8a735", alpha=0.85)
    ax.bar(x, stats["avg_clay_pct"], w, bottom=stats["avg_sand_pct"], label="Clay", color="#c25b3a", alpha=0.85)
    ax.bar(x, stats["avg_silt_pct"], w,
           bottom=stats["avg_sand_pct"] + stats["avg_clay_pct"],
           label="Silt", color="#7ba748", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(stats["grower_label"])
    ax.set_ylabel("Percent (%)")
    ax.set_title("Soil texture composition by state (SSURGO)")
    ax.legend()
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


PLOT_FUNCTIONS = {
    "boundaries": [
        ("field_area_histogram", plot_field_area_histogram),
        ("field_size_summary", plot_field_size_summary),
        ("field_area_comparison", plot_field_area_comparison),
    ],
    "cdl": [
        ("crop_composition", plot_crop_composition),
        ("crop_diversity", plot_crop_diversity),
        ("corn_soy_rotation", plot_corn_soy_rotation),
    ],
    "weather": [
        ("monthly_temperature", plot_monthly_temperature),
        ("annual_precipitation", plot_annual_precipitation),
        ("gdd_comparison", plot_gdd_comparison),
    ],
    "geospatial": [
        ("grower_overview_map", plot_grower_overview_map),
    ],
    "soil": [
        ("soil_ph", plot_soil_ph),
        ("soil_om", plot_soil_om),
        ("soil_texture", plot_soil_texture),
    ],
}


def run_all(
    grower_data: dict,
    output_base: Path,
    categories: list[str] | None = None,
) -> list[Path]:
    if categories is None:
        categories = list(PLOT_FUNCTIONS.keys())

    generated: list[Path] = []

    if "boundaries" in categories and not grower_data["boundaries"].empty:
        for name, func in PLOT_FUNCTIONS["boundaries"]:
            p = func(grower_data["boundaries"], output_base)
            generated.append(p)

    if "cdl" in categories and not grower_data["rotations"].empty:
        has_comp = not grower_data.get("composition", pd.DataFrame()).empty
        for name, func in PLOT_FUNCTIONS["cdl"]:
            if name == "crop_composition" and has_comp:
                p = func(grower_data["composition"], output_base)
                generated.append(p)
            elif name != "crop_composition":
                p = func(grower_data["rotations"], output_base)
                generated.append(p)

    if "weather" in categories and not grower_data["weather"].empty:
        for name, func in PLOT_FUNCTIONS["weather"]:
            p = func(grower_data["weather"], output_base)
            generated.append(p)

    if "geospatial" in categories and not grower_data["boundaries"].empty:
        for name, func in PLOT_FUNCTIONS["geospatial"]:
            p = func(grower_data["boundaries"], output_base)
            generated.append(p)

    if "soil" in categories and not grower_data.get("soil", pd.DataFrame()).empty:
        for name, func in PLOT_FUNCTIONS["soil"]:
            p = func(grower_data["soil"], output_base)
            generated.append(p)

    return generated

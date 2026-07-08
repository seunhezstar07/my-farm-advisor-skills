from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import geopandas as gpd


FIELD_COLORS = [
    "#1b9e77", "#d95f02", "#7570b3", "#e7298a",
    "#66a61e", "#e6ab02", "#a6761d", "#666666",
]


def _color_for_index(idx: int) -> str:
    return FIELD_COLORS[idx % len(FIELD_COLORS)]


def _html_escape(value: Any) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _discover_farms(grower_root: Path, grower_slug: str) -> list[dict[str, str]]:
    farms: list[dict[str, str]] = []
    farms_dir = grower_root / "farms"
    if not farms_dir.is_dir():
        return farms
    for farm_dir in sorted(farms_dir.iterdir()):
        if not farm_dir.is_dir():
            continue
        boundary_path = farm_dir / "boundary" / "field_boundaries.geojson"
        if boundary_path.exists():
            farms.append({
                "slug": farm_dir.name,
                "boundary_path": str(boundary_path),
            })
    return farms


def _load_fields(farm: dict[str, str], farm_name: str) -> list[dict[str, Any]]:
    path = Path(farm["boundary_path"])
    gdf = gpd.read_file(path)
    gdf = gdf.to_crs("EPSG:4326")
    fields: list[dict[str, Any]] = []
    for _, row in gdf.iterrows():
        props = dict(row.drop("geometry"))
        geom = row.geometry
        if geom is None:
            continue
        field_id = str(props.get("field_id", ""))
        fields.append({
            "farm_slug": farm["slug"],
            "farm_name": farm_name,
            "field_id": field_id,
            "properties": {k: v for k, v in props.items() if k != "field_id"},
            "geometry": json.loads(gpd.GeoSeries([geom]).to_json())["features"][0]["geometry"],
        })
    return fields


def _build_geojson(fields: list[dict[str, Any]]) -> dict[str, Any]:
    features: list[dict[str, Any]] = []
    for field in fields:
        feature: dict[str, Any] = {
            "type": "Feature",
            "properties": {
                "field_id": field["field_id"],
                "farm_slug": field["farm_slug"],
                "farm_name": field["farm_name"],
                **field["properties"],
            },
            "geometry": field["geometry"],
        }
        features.append(feature)
    return {"type": "FeatureCollection", "features": features}


def _compute_center(geojson: dict[str, Any]) -> tuple[float, float]:
    lats: list[float] = []
    lons: list[float] = []
    for feature in geojson["features"]:
        coords = _extract_coords(feature["geometry"])
        for lon, lat in coords:
            lats.append(lat)
            lons.append(lon)
    if not lats:
        return 40.0, -93.0
    return sum(lats) / len(lats), sum(lons) / len(lons)


def _extract_coords(geometry: dict[str, Any]) -> list[list[float]]:
    if geometry["type"] == "Polygon":
        return geometry["coordinates"][0]
    if geometry["type"] == "MultiPolygon":
        result: list[list[float]] = []
        for poly in geometry["coordinates"]:
            result.extend(poly[0])
        return result
    return []


def _field_list_html(fields: list[dict[str, Any]]) -> str:
    items: list[str] = []
    for idx, field in enumerate(fields):
        fid = _html_escape(field["field_id"])
        farm = _html_escape(field["farm_name"])
        label = f"{fid}"
        items.append(
            f'<div class="field-item" onclick="zoomToField({idx})" '
            f'title="{farm}">{label}</div>'
        )
    return "\n".join(items)


def _popup_html(field: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"<b>Field:</b> {_html_escape(field['field_id'])}")
    lines.append(f"<b>Farm:</b> {_html_escape(field['farm_name'])}")
    for key, value in field["properties"].items():
        label = key.replace("_", " ").title()
        lines.append(f"<b>{_html_escape(label)}:</b> {_html_escape(value)}")
    return "<br>".join(lines)


def build_grower_map_html(
    grower_slug: str,
    grower_root: Path,
    output_path: Path,
) -> Path:
    farms = _discover_farms(grower_root, grower_slug)
    if not farms:
        raise ValueError(f"No farms found for grower '{grower_slug}'")

    all_fields: list[dict[str, Any]] = []
    farm_names: dict[str, str] = {}
    for farm in farms:
        slug = farm["slug"]
        name = slug.replace("-", " ").title().replace("I L ", "IL ").replace("I A ", "IA ")
        farm_names[slug] = name
        loaded = _load_fields(farm, name)
        all_fields.extend(loaded)

    if not all_fields:
        raise ValueError(f"No fields found for grower '{grower_slug}'")

    geojson = _build_geojson(all_fields)
    center_lat, center_lon = _compute_center(geojson)
    field_list_html = _field_list_html(all_fields)

    popups_js_lines: list[str] = []
    for idx, field in enumerate(all_fields):
        popups_js_lines.append(
            f"  popups[{idx}] = '{_html_escape(_popup_html(field))}';"
        )
    popups_js = "\n".join(popups_js_lines)

    geojson_str = json.dumps(geojson, separators=(",", ":"))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Grower Map — {_html_escape(grower_slug)}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
#container {{ display: flex; height: 100vh; }}
#sidebar {{
  width: 280px; background: #f5f5f5; border-right: 1px solid #ccc;
  overflow-y: auto; padding: 12px;
}}
#sidebar h2 {{ font-size: 1.1em; margin-bottom: 8px; color: #1a1a1a; }}
#sidebar .grower-label {{ font-size: 0.85em; color: #555; margin-bottom: 12px; }}
.field-item {{
  padding: 6px 10px; margin: 2px 0; cursor: pointer; border-radius: 4px;
  font-size: 0.9em; background: #fff; border: 1px solid #ddd;
  transition: background 0.15s;
}}
.field-item:hover {{ background: #e3f2fd; }}
#map {{ flex: 1; }}
.leaflet-popup-content {{ font-size: 0.9em; line-height: 1.5; }}
</style>
</head>
<body>
<div id="container">
  <div id="sidebar">
    <h2>{_html_escape(grower_slug)}</h2>
    <div class="grower-label">{len(all_fields)} field(s) across {len(farms)} farm(s)</div>
    <div id="field-list">{field_list_html}</div>
  </div>
  <div id="map"></div>
</div>
<script>
var fieldData = {geojson_str};

var map = L.map('map');

var colors = {json.dumps(FIELD_COLORS, separators=(",", ":"))};

var popups = {{}};
{popups_js}

var fieldLayers = [];
fieldData.features.forEach(function(feature, idx) {{
  var color = colors[idx % colors.length];
  var layer = L.geoJSON(feature, {{
    style: {{
      color: color, weight: 2, fillColor: color, fillOpacity: 0.25,
    }},
    onEachFeature: function(f, l) {{
      l.bindPopup(popups[idx]);
    }}
  }});
  fieldLayers.push(layer);
  layer.addTo(map);
}});

function zoomToField(idx) {{
  var layer = fieldLayers[idx];
  if (layer) {{
    map.fitBounds(layer.getBounds(), {{maxZoom: 18, padding: [30, 30]}});
  }}
}}

L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  attribution: '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  maxZoom: 19,
}}).addTo(map);

if (fieldLayers.length > 0) {{
  var group = L.featureGroup(fieldLayers);
  map.fitBounds(group.getBounds(), {{padding: [20, 20]}});
}}
</script>
</body>
</html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path

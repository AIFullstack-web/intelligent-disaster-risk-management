from pathlib import Path
import osmium
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString, box

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

BRIDGES = DATA / "processed" / "bridge_rainfall_grid_mapping.csv"
PBF = DATA / "external" / "osm" / "eastern-zone-latest.osm.pbf"
OUTPUT = DATA / "processed" / "bridge_river_features.csv"

WATERWAY_TYPES = {
    "river", "stream", "canal", "drain", "ditch",
    "wadi", "brook", "tidal_channel", "fairway"
}

METRIC_CRS = (
    "+proj=aeqd +lat_0=20.5 +lon_0=84.5 "
    "+datum=WGS84 +units=m +no_defs +type=crs"
)

def stop(message):
    raise ValueError(message)

if OUTPUT.exists():
    raise FileExistsError(f"Refusing to overwrite: {OUTPUT}")

if not BRIDGES.exists():
    stop(f"Bridge mapping not found: {BRIDGES}")

if not PBF.exists():
    stop(f"OSM PBF not found: {PBF}")

bridges = pd.read_csv(
    BRIDGES,
    usecols=["asset_id", "latitude", "longitude"],
    low_memory=False
)

if bridges["asset_id"].duplicated().any():
    stop("Duplicate asset IDs found in bridge mapping.")

if bridges[["latitude", "longitude"]].isna().any().any():
    stop("Missing bridge coordinates found.")

# Expand the bridge inventory bounds to retain nearby waterway segments.
study_box = box(
    bridges["longitude"].min() - 0.75,
    bridges["latitude"].min() - 0.75,
    bridges["longitude"].max() + 0.75,
    bridges["latitude"].max() + 0.75,
)

class WaterwayHandler(osmium.SimpleHandler):
    def __init__(self, clip_box):
        super().__init__()
        self.clip_box = clip_box
        self.rows = []
        self.invalid_ways = 0

    def way(self, way):
        waterway_type = way.tags.get("waterway")
        if waterway_type not in WATERWAY_TYPES:
            return

        coords = []
        for node in way.nodes:
            if not node.location.valid():
                self.invalid_ways += 1
                return
            coords.append((node.location.lon, node.location.lat))

        if len(coords) < 2:
            return

        try:
            line = LineString(coords)
            if line.is_empty or not line.is_valid:
                return
            if not line.intersects(self.clip_box):
                return
        except Exception:
            return

        self.rows.append({
            "waterway_osm_id": str(way.id),
            "waterway_type": waterway_type,
            "waterway_name": way.tags.get("name", ""),
            "geometry": line,
        })

print("READING_OSM_PBF:", PBF)
handler = WaterwayHandler(study_box)
handler.apply_file(str(PBF), locations=True)

if not handler.rows:
    stop("No usable waterway lines found in the study area.")

waterways = gpd.GeoDataFrame(
    pd.DataFrame(handler.rows),
    geometry="geometry",
    crs="EPSG:4326"
)

# Remove duplicate OSM IDs if the extract contains repeated ways.
waterways = waterways.drop_duplicates(
    subset=["waterway_osm_id"]
).reset_index(drop=True)

bridge_points = gpd.GeoDataFrame(
    bridges.copy(),
    geometry=gpd.points_from_xy(
        bridges["longitude"], bridges["latitude"]
    ),
    crs="EPSG:4326"
)

bridges_m = bridge_points.to_crs(METRIC_CRS)
waterways_m = waterways.to_crs(METRIC_CRS)

print("BRIDGES:", len(bridges_m))
print("WATERWAY_LINES:", len(waterways_m))
print("INVALID_WAYS_SKIPPED:", handler.invalid_ways)
print("WATERWAY_TYPES:")
print(waterways["waterway_type"].value_counts().to_string())

# Spatial-index nearest join: all distances are measured in metres
# after transforming both layers into the same projected CRS.
joined = gpd.sjoin_nearest(
    bridges_m,
    waterways_m[
        ["waterway_osm_id", "waterway_type", "waterway_name", "geometry"]
    ],
    how="left",
    distance_col="distance_to_waterway_m"
)

if joined["distance_to_waterway_m"].isna().any():
    stop("Some bridges did not receive a nearest-waterway match.")

# Resolve equal-distance ties deterministically.
joined = joined.sort_values(
    ["asset_id", "distance_to_waterway_m", "waterway_osm_id"]
)
joined = joined.drop_duplicates("asset_id", keep="first")

result = pd.DataFrame({
    "asset_id": joined["asset_id"].to_numpy(),
    "distance_to_waterway_km": (
        joined["distance_to_waterway_m"].to_numpy() / 1000.0
    ),
    "nearest_waterway_osm_id": joined["waterway_osm_id"].to_numpy(),
    "nearest_waterway_type": joined["waterway_type"].to_numpy(),
    "nearest_waterway_name": joined["waterway_name"].fillna("").to_numpy(),
})

if len(result) != bridges["asset_id"].nunique():
    stop("Output bridge count does not match the source mapping.")

if result["asset_id"].duplicated().any():
    stop("Duplicate asset IDs in output.")

if (
    result["distance_to_waterway_km"].isna().any()
    or (result["distance_to_waterway_km"] < 0).any()
    or not np.isfinite(result["distance_to_waterway_km"]).all()
):
    stop("Invalid distance values found.")

result.to_csv(OUTPUT, index=False)

dist = result["distance_to_waterway_km"]

print("\nOUTPUT:", OUTPUT)
print("OUTPUT_ROWS:", len(result))
print("UNIQUE_BRIDGES:", result["asset_id"].nunique())
print("MEAN_DISTANCE_KM:", round(float(dist.mean()), 3))
print("MEDIAN_DISTANCE_KM:", round(float(dist.median()), 3))
print("P95_DISTANCE_KM:", round(float(dist.quantile(0.95)), 3))
print("MAX_DISTANCE_KM:", round(float(dist.max()), 3))
print("BRIDGES_WITHIN_1KM:", int((dist <= 1).sum()))
print("BRIDGES_WITHIN_5KM:", int((dist <= 5).sum()))
print("BRIDGES_OVER_10KM:", int((dist > 10).sum()))
print("BRIDGES_OVER_25KM:", int((dist > 25).sum()))
print("MISSING_DISTANCES:", int(dist.isna().sum()))
print("OUTPUT_VALIDATION: PASSED")

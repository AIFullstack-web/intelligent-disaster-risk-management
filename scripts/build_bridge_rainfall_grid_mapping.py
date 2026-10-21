from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
from netCDF4 import Dataset
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
INPUT = DATA / "processed" / "bridge_flood_event_dataset.csv"
BOUNDARY = DATA / "external" / "boundaries" / "india_adm1.geojson"
OUTPUT = DATA / "processed" / "bridge_rainfall_grid_mapping.csv"

def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1 = np.radians(lat1), np.radians(lon1)
    lat2, lon2 = np.radians(lat2), np.radians(lon2)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    )
    return 6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))

def read_rainfall_validity(year):
    path = DATA / "raw" / "imd_rainfall_probe" / f"RF25_{year}_probe.nc"
    with Dataset(path) as ds:
        lon = np.asarray(ds.variables["LONGITUDE"][:])
        lat = np.asarray(ds.variables["LATITUDE"][:])
        var = ds.variables["RAINFALL"]
        masked = var[:]
        values = np.asarray(masked.filled(np.nan), dtype=float)
        invalid = (
            np.ma.getmaskarray(masked)
            | ~np.isfinite(values)
            | (values == -999)
        )
        valid = (~invalid).all(axis=0)
    return lon, lat, valid

if OUTPUT.exists():
    raise FileExistsError(f"Refusing to overwrite: {OUTPUT}")

lon14, lat14, valid14 = read_rainfall_validity(2014)
lon15, lat15, valid15 = read_rainfall_validity(2015)

if not np.array_equal(lon14, lon15) or not np.array_equal(lat14, lat15):
    raise ValueError("Rainfall grids differ between 2014 and 2015.")

valid_both = valid14 & valid15
valid_y, valid_x = np.where(valid_both)
valid_lat = lat14[valid_y]
valid_lon = lon14[valid_x]

if len(valid_y) == 0:
    raise ValueError("No grid cells are complete in both years.")

bridges = pd.read_csv(
    INPUT,
    usecols=["asset_id", "osm_id", "latitude", "longitude"],
    low_memory=False
)

coordinate_counts = bridges.groupby("asset_id")[
    ["latitude", "longitude"]
].nunique()

if (coordinate_counts > 1).any().any():
    raise ValueError("Some asset IDs have inconsistent coordinates.")

bridges = bridges.drop_duplicates("asset_id").reset_index(drop=True)
bridge_lat = bridges["latitude"].to_numpy()
bridge_lon = bridges["longitude"].to_numpy()

orig_y = np.abs(
    bridge_lat[:, None] - lat14[None, :]
).argmin(axis=1)

orig_x = np.abs(
    bridge_lon[:, None] - lon14[None, :]
).argmin(axis=1)

unique_cells = np.unique(np.column_stack([orig_y, orig_x]), axis=0)
source_by_cell = {}

for y, x in unique_cells:
    y, x = int(y), int(x)

    if valid_both[y, x]:
        source_by_cell[(y, x)] = (y, x, 0.0)
    else:
        distances = haversine(
            lat14[y], lon14[x], valid_lat, valid_lon
        )
        k = int(np.argmin(distances))
        sy, sx = int(valid_y[k]), int(valid_x[k])
        shift_km = float(distances[k])

        if not (valid14[sy, sx] and valid15[sy, sx]):
            raise ValueError("Selected source grid is not valid in both years.")

        source_by_cell[(y, x)] = (sy, sx, shift_km)

source_y = np.empty(len(bridges), dtype=int)
source_x = np.empty(len(bridges), dtype=int)
shift_km = np.empty(len(bridges), dtype=float)

for i, (y, x) in enumerate(zip(orig_y, orig_x)):
    source_y[i], source_x[i], shift_km[i] = source_by_cell[
        (int(y), int(x))
    ]

proxy_used = ~valid_both[orig_y, orig_x]

bridge_to_original = haversine(
    bridge_lat, bridge_lon, lat14[orig_y], lon14[orig_x]
)
bridge_to_source = haversine(
    bridge_lat, bridge_lon, lat14[source_y], lon14[source_x]
)

boundary = gpd.read_file(BOUNDARY)
odisha = boundary[
    boundary["shapeName"].astype(str).str.casefold() == "odisha"
].to_crs("EPSG:4326")

if odisha.empty:
    raise ValueError("Odisha boundary was not found.")

odisha_geom = odisha.geometry.union_all()
source_inside = np.array([
    odisha_geom.covers(Point(lon14[x], lat14[y]))
    for y, x in zip(source_y, source_x)
])

result = pd.DataFrame({
    "asset_id": bridges["asset_id"],
    "osm_id": bridges["osm_id"],
    "latitude": bridge_lat,
    "longitude": bridge_lon,
    "original_grid_lat": lat14[orig_y],
    "original_grid_lon": lon14[orig_x],
    "original_grid_valid_2014": valid14[orig_y, orig_x],
    "original_grid_valid_2015": valid15[orig_y, orig_x],
    "rainfall_grid_lat": lat14[source_y],
    "rainfall_grid_lon": lon14[source_x],
    "rainfall_grid_proxy_used": proxy_used,
    "grid_center_shift_km": shift_km,
    "bridge_to_original_grid_km": bridge_to_original,
    "bridge_to_rainfall_grid_km": bridge_to_source,
    "rainfall_source_inside_odisha": source_inside,
    "rainfall_source_valid_2014": valid14[source_y, source_x],
    "rainfall_source_valid_2015": valid15[source_y, source_x],
})

if not result["rainfall_source_valid_2014"].all():
    raise ValueError("Invalid 2014 source cells found.")

if not result["rainfall_source_valid_2015"].all():
    raise ValueError("Invalid 2015 source cells found.")

result.to_csv(OUTPUT, index=False)

print("OUTPUT:", OUTPUT)
print("UNIQUE_BRIDGES:", len(result))
print("ORIGINAL_GRID_CELLS:", len(unique_cells))
print("VALID_GRID_CELLS_IN_BOTH_YEARS:", int(valid_both.sum()))
print("BRIDGES_USING_PROXY:", int(proxy_used.sum()))
print("UNIQUE_SELECTED_RAINFALL_CELLS:",
      result[["rainfall_grid_lat", "rainfall_grid_lon"]].drop_duplicates().shape[0])
print("BRIDGE_TO_SOURCE_DISTANCE_MEAN_KM:",
      round(float(bridge_to_source.mean()), 2))
print("BRIDGE_TO_SOURCE_DISTANCE_P95_KM:",
      round(float(np.percentile(bridge_to_source, 95)), 2))
print("BRIDGE_TO_SOURCE_DISTANCE_MAX_KM:",
      round(float(bridge_to_source.max()), 2))
print("SOURCES_OUTSIDE_ODISHA:", int((~source_inside).sum()))
print("SOURCE_VALIDITY_CHECK: PASSED")

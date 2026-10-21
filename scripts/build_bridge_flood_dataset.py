import geopandas as gpd
import pandas as pd
from pathlib import Path

BRIDGES = Path("data/processed/odisha_bridge_inventory_boundary_filtered.geojson")
FLOODS = Path("data/external/India-Flood-Inventory/Shapefile_corrected/india_flood_inventory_corrected.shp")
OUT = Path("data/processed/bridge_flood_event_dataset.csv")

bridges = gpd.read_file(BRIDGES)
floods = gpd.read_file(FLOODS)

floods = floods[
    floods["State"].astype(str).str.contains(
        "ODISHA|ORISSA",
        case=False,
        na=False
    )
].copy()

floods["StartDate"] = pd.to_datetime(
    floods["StartDate"],
    dayfirst=True,
    errors="coerce"
)

floods["EndDate"] = pd.to_datetime(
    floods["EndDate"],
    dayfirst=True,
    errors="coerce"
)

events = floods.dissolve(
    by="FID",
    aggfunc={
        "StartDate": "min",
        "EndDate": "max",
        "State": "first",
        "MainCause": "first"
    }
).reset_index()

events = events[
    ["FID", "StartDate", "EndDate", "State", "MainCause", "geometry"]
].copy()

bridges = bridges[
    ["asset_id", "osm_id", "name", "highway", "lanes",
     "surface", "ref", "length_m", "latitude",
     "longitude", "geometry"]
].copy()

bridges = bridges.drop_duplicates("asset_id")
events = events.drop_duplicates("FID")

bridge_rows = bridges.drop(columns="geometry").copy()
bridge_rows["_key"] = 1

event_rows = events.drop(columns="geometry").copy()
event_rows["_key"] = 1

pairs = bridge_rows.merge(
    event_rows,
    on="_key",
    how="outer"
).drop(columns="_key")

positive = gpd.sjoin(
    bridges[["asset_id", "geometry"]],
    events[["FID", "geometry"]],
    how="inner",
    predicate="intersects"
)[["asset_id", "FID"]].drop_duplicates()

positive["flood_exposed"] = 1

pairs = pairs.merge(
    positive,
    on=["asset_id", "FID"],
    how="left"
)

pairs["flood_exposed"] = (
    pairs["flood_exposed"]
    .fillna(0)
    .astype("int8")
)

pairs["event_id"] = pairs["FID"]

pairs = pairs[
    [
        "asset_id",
        "osm_id",
        "name",
        "highway",
        "lanes",
        "surface",
        "ref",
        "length_m",
        "latitude",
        "longitude",
        "event_id",
        "StartDate",
        "EndDate",
        "State",
        "MainCause",
        "flood_exposed"
    ]
]

pairs = pairs.sort_values(
    ["event_id", "asset_id"]
).reset_index(drop=True)

OUT.parent.mkdir(parents=True, exist_ok=True)
pairs.to_csv(OUT, index=False)

print("BRIDGES:", bridges["asset_id"].nunique())
print("FLOOD EVENTS:", events["FID"].nunique())
print("EXPECTED ROWS:", bridges["asset_id"].nunique() * events["FID"].nunique())
print("ACTUAL ROWS:", len(pairs))
print("POSITIVE:", int(pairs["flood_exposed"].sum()))
print("NEGATIVE:", int((pairs["flood_exposed"] == 0).sum()))
print("POSITIVE RATE:", round(pairs["flood_exposed"].mean(), 4))

print()
print("EVENT LABEL COUNTS:")
print(
    pairs.groupby("event_id")["flood_exposed"]
    .agg(["count", "sum"])
    .to_string()
)

print()
print("SAVED:", OUT)

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

SOURCE = DATA / "bridge_event_ml_features.csv"
RIVER = DATA / "bridge_river_features.csv"
OUTPUT = DATA / "bridge_event_ml_features_with_river.csv"

if OUTPUT.exists():
    raise FileExistsError(f"Refusing to overwrite: {OUTPUT}")

events = pd.read_csv(SOURCE, low_memory=False)
river = pd.read_csv(RIVER, low_memory=False)

required = {
    "asset_id",
    "distance_to_waterway_km",
    "nearest_waterway_type",
}
missing = required - set(river.columns)

if missing:
    raise ValueError(f"Missing river feature columns: {sorted(missing)}")

if river["asset_id"].duplicated().any():
    raise ValueError("Duplicate asset IDs in the river feature file.")

river["distance_to_waterway_km"] = pd.to_numeric(
    river["distance_to_waterway_km"], errors="raise"
)

dist = river["distance_to_waterway_km"].to_numpy(dtype=float)

if not np.isfinite(dist).all() or (dist < 0).any():
    raise ValueError("Invalid river-distance values found.")

river["nearest_waterway_type"] = (
    river["nearest_waterway_type"]
    .fillna("unknown")
    .astype(str)
    .str.strip()
    .replace("", "unknown")
)

river = river[
    [
        "asset_id",
        "distance_to_waterway_km",
        "nearest_waterway_type",
    ]
]

if events.duplicated(["asset_id", "event_id"]).any():
    raise ValueError("Duplicate bridge-event rows in the source dataset.")

merged = events.merge(
    river,
    on="asset_id",
    how="left",
    validate="many_to_one",
    indicator=True,
)

unmatched = int((merged["_merge"] != "both").sum())

if unmatched:
    raise ValueError(f"Unmatched event rows: {unmatched}")

merged = merged.drop(columns="_merge")

if len(merged) != len(events):
    raise ValueError("Output row count does not match source.")

if merged.duplicated(["asset_id", "event_id"]).any():
    raise ValueError("Duplicate bridge-event pairs in output.")

if merged[
    ["distance_to_waterway_km", "nearest_waterway_type"]
].isna().any().any():
    raise ValueError("Missing river features remain after merging.")

original = (
    events.set_index(["asset_id", "event_id"])["flood_exposed"]
    .sort_index()
)
updated = (
    merged.set_index(["asset_id", "event_id"])["flood_exposed"]
    .sort_index()
)

if not original.equals(updated):
    raise ValueError("Exposure labels changed during merge.")

merged.to_csv(OUTPUT, index=False)

print("OUTPUT:", OUTPUT)
print("ROWS:", len(merged))
print("UNIQUE_BRIDGES:", merged["asset_id"].nunique())
print("UNIQUE_EVENTS:", merged["event_id"].nunique())
print("MISSING_RIVER_FEATURES:", int(
    merged[
        ["distance_to_waterway_km", "nearest_waterway_type"]
    ].isna().sum().sum()
))
print("EXPOSURE_LABELS_UNCHANGED: PASSED")
print("BRIDGE_EVENT_KEYS_UNCHANGED: PASSED")
print("RIVER_FEATURES_MERGED: PASSED")
print("\nWATERWAY TYPE COUNTS BY UNIQUE BRIDGE:")
print(
    river["nearest_waterway_type"]
    .value_counts()
    .to_string()
)

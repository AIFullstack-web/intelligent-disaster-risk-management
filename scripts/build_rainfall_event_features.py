from pathlib import Path
import numpy as np
import pandas as pd
from netCDF4 import Dataset, num2date

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
EVENTS = DATA / "processed" / "bridge_flood_event_dataset.csv"
MAPPING = DATA / "processed" / "bridge_rainfall_grid_mapping.csv"
OUTPUT = DATA / "processed" / "bridge_event_ml_features.csv"

FEATURES = [
    "rain_sum_3d_pre_event_mm",
    "rain_sum_7d_pre_event_mm",
    "rain_sum_14d_pre_event_mm",
    "rain_max_3d_pre_event_mm",
    "rain_max_7d_pre_event_mm",
    "rain_max_14d_pre_event_mm",
    "rain_mean_7d_pre_event_mm",
    "rain_mean_14d_pre_event_mm",
]

MAP_COLUMNS = [
    "asset_id",
    "original_grid_lat",
    "original_grid_lon",
    "original_grid_valid_2014",
    "original_grid_valid_2015",
    "rainfall_grid_lat",
    "rainfall_grid_lon",
    "rainfall_grid_proxy_used",
    "grid_center_shift_km",
    "bridge_to_original_grid_km",
    "bridge_to_rainfall_grid_km",
    "rainfall_source_inside_odisha",
    "rainfall_source_valid_2014",
    "rainfall_source_valid_2015",
]

def fail(message):
    raise ValueError(message)

def valid_boolean(series):
    return series.astype(str).str.lower().eq("true")

if OUTPUT.exists():
    raise FileExistsError(f"Refusing to overwrite: {OUTPUT}")

events = pd.read_csv(EVENTS, low_memory=False)
mapping = pd.read_csv(MAPPING, low_memory=False)

required_event_cols = {
    "asset_id", "event_id", "StartDate", "flood_exposed"
}
if not required_event_cols.issubset(events.columns):
    fail("The event dataset is missing required columns.")

if not set(MAP_COLUMNS).issubset(mapping.columns):
    fail("The mapping file is missing required columns.")

if events.duplicated(["asset_id", "event_id"]).any():
    fail("Duplicate bridge-event pairs found in the source dataset.")

if mapping["asset_id"].duplicated().any():
    fail("The mapping file contains duplicate asset IDs.")

if len(mapping) != events["asset_id"].nunique():
    fail("Mapping count does not match the unique bridge count.")

for col in [
    "rainfall_source_valid_2014",
    "rainfall_source_valid_2015",
]:
    if not valid_boolean(mapping[col]).all():
        fail(f"Invalid selected rainfall source detected: {col}")

events["StartDate"] = pd.to_datetime(
    events["StartDate"], errors="raise"
).dt.normalize()

event_dates = events[["event_id", "StartDate"]].drop_duplicates()

if event_dates["event_id"].duplicated().any():
    fail("An event ID has more than one start date.")

if event_dates["StartDate"].dt.year.nunique() == 0:
    fail("No usable event dates were found.")

mapped = events.merge(
    mapping[MAP_COLUMNS],
    on="asset_id",
    how="left",
    validate="many_to_one",
    indicator=True,
)

if not mapped["_merge"].eq("both").all():
    fail("Some bridges did not receive a rainfall-grid mapping.")

mapped = mapped.drop(columns="_merge")

cell_table = mapping[
    ["rainfall_grid_lat", "rainfall_grid_lon"]
].drop_duplicates()

feature_records = []

for year, year_events in event_dates.groupby(event_dates["StartDate"].dt.year):
    nc_path = (
        DATA / "raw" / "imd_rainfall_probe"
        / f"RF25_{year}_probe.nc"
    )

    if not nc_path.exists():
        fail(f"Missing rainfall file: {nc_path}")

    with Dataset(nc_path, "r") as ds:
        lon = np.asarray(ds.variables["LONGITUDE"][:])
        lat = np.asarray(ds.variables["LATITUDE"][:])
        time_var = ds.variables["TIME"]
        time_values = time_var[:]

        dates = num2date(
            time_values,
            units=time_var.units,
            calendar=getattr(time_var, "calendar", "standard"),
        )
        timeline = [
            pd.Timestamp(year=d.year, month=d.month, day=d.day)
            for d in dates
        ]
        date_to_index = {
            date: i for i, date in enumerate(timeline)
        }

        if (
            not timeline
            or timeline[0] != pd.Timestamp(year, 1, 1)
            or timeline[-1] != pd.Timestamp(year, 12, 31)
        ):
            fail(f"Unexpected date coverage in rainfall file for {year}.")

        rain = ds.variables["RAINFALL"]

        for event in year_events.itertuples(index=False):
            start_date = event.StartDate

            if start_date not in date_to_index:
                fail(f"Event start date not present in rainfall data: {start_date}")

            start_idx = date_to_index[start_date]

            if start_idx < 14:
                fail(f"Insufficient 14-day antecedent history for {event.event_id}")

            expected_dates = list(pd.date_range(
                start=start_date - pd.Timedelta(days=14),
                end=start_date - pd.Timedelta(days=1),
                freq="D",
            ))

            actual_dates = timeline[start_idx - 14:start_idx]
            if actual_dates != expected_dates:
                fail(f"Antecedent date window is not continuous for {event.event_id}")

            for cell in cell_table.itertuples(index=False):
                iy = int(np.abs(lat - cell.rainfall_grid_lat).argmin())
                ix = int(np.abs(lon - cell.rainfall_grid_lon).argmin())

                if (
                    not np.isclose(lat[iy], cell.rainfall_grid_lat, atol=1e-5)
                    or not np.isclose(lon[ix], cell.rainfall_grid_lon, atol=1e-5)
                ):
                    fail("Could not match mapped grid coordinates to NetCDF grid.")

                raw = np.ma.asarray(
                    rain[start_idx - 14:start_idx, iy, ix]
                )
                values = np.asarray(raw.filled(np.nan), dtype=float)

                invalid = (
                    np.ma.getmaskarray(raw)
                    | ~np.isfinite(values)
                    | (values == -999)
                )

                if len(values) != 14 or invalid.any():
                    fail(
                        f"Invalid antecedent rainfall: event={event.event_id}, "
                        f"grid=({cell.rainfall_grid_lat}, "
                        f"{cell.rainfall_grid_lon})"
                    )

                w3 = values[-3:]
                w7 = values[-7:]
                w14 = values

                feature_records.append({
                    "event_id": event.event_id,
                    "rainfall_grid_lat": cell.rainfall_grid_lat,
                    "rainfall_grid_lon": cell.rainfall_grid_lon,
                    "rain_sum_3d_pre_event_mm": float(w3.sum()),
                    "rain_sum_7d_pre_event_mm": float(w7.sum()),
                    "rain_sum_14d_pre_event_mm": float(w14.sum()),
                    "rain_max_3d_pre_event_mm": float(w3.max()),
                    "rain_max_7d_pre_event_mm": float(w7.max()),
                    "rain_max_14d_pre_event_mm": float(w14.max()),
                    "rain_mean_7d_pre_event_mm": float(w7.mean()),
                    "rain_mean_14d_pre_event_mm": float(w14.mean()),
                })

feature_df = pd.DataFrame(feature_records)
join_cols = [
    "event_id", "rainfall_grid_lat", "rainfall_grid_lon"
]

if feature_df.duplicated(join_cols).any():
    fail("Duplicate event/grid feature records were generated.")

if feature_df[FEATURES].isna().any().any():
    fail("Missing feature values detected.")

result = mapped.merge(
    feature_df,
    on=join_cols,
    how="left",
    validate="many_to_one",
    indicator=True,
)

if not result["_merge"].eq("both").all():
    fail("Some bridge-event rows did not receive rainfall features.")

result = result.drop(columns="_merge")

if len(result) != len(events):
    fail("Output row count differs from the source event dataset.")

if result.duplicated(["asset_id", "event_id"]).any():
    fail("Output contains duplicate bridge-event pairs.")

before = (
    events.set_index(["asset_id", "event_id"])["flood_exposed"]
    .sort_index()
)
after = (
    result.set_index(["asset_id", "event_id"])["flood_exposed"]
    .sort_index()
)

if not before.equals(after):
    fail("Target labels changed during feature generation.")

if result[FEATURES].isna().any().any():
    fail("Output contains missing rainfall features.")

result.to_csv(OUTPUT, index=False)

print("OUTPUT:", OUTPUT)
print("ROWS:", len(result))
print("UNIQUE_BRIDGES:", result["asset_id"].nunique())
print("UNIQUE_EVENTS:", result["event_id"].nunique())
print("DUPLICATE_BRIDGE_EVENT_PAIRS:",
      int(result.duplicated(["asset_id", "event_id"]).sum()))
print("RAINFALL_FEATURE_COUNT:", len(FEATURES))
print("MISSING_RAINFALL_FEATURE_VALUES:",
      int(result[FEATURES].isna().sum().sum()))
print("PROXY_BRIDGES:", int(mapping["rainfall_grid_proxy_used"].sum()))
print("TARGET_UNCHANGED: PASSED")
print("TEMPORAL_ALIGNMENT: PASSED")
print("SOURCE_VALIDITY: PASSED")

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "bridge_event_ml_features.csv"
OUT = ROOT / "artifacts" / "five_algorithm_comparison"
MODEL_PATH = OUT / "selected_experimental_random_forest.joblib"
META_PATH = OUT / "selected_experimental_random_forest_metadata.json"

TARGET = "flood_exposed"
DATE = "StartDate"
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


def main():
    if not DATA.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA}")
    if not (OUT / "cv_model_summary.csv").exists():
        raise FileNotFoundError("Cross-validation results not found.")
    if not (OUT / "test_model_metrics.csv").exists():
        raise FileNotFoundError("Holdout evaluation results not found.")
    if MODEL_PATH.exists() or META_PATH.exists():
        raise FileExistsError(
            "Model artifact or metadata already exists. "
            "Review existing files; nothing was overwritten."
        )

    df = pd.read_csv(DATA, low_memory=False)
    required = set(FEATURES + [TARGET, DATE, "asset_id", "event_id"])
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    df[DATE] = pd.to_datetime(df[DATE], errors="raise")
    years = set(df[DATE].dt.year.unique())
    if years != {2014, 2015}:
        raise ValueError(f"Expected 2014 and 2015 data; found {sorted(years)}")

    train_mask = df[DATE].dt.year.eq(2014)
    train = df.loc[train_mask].copy()
    X = train[FEATURES].apply(pd.to_numeric, errors="coerce")
    y = pd.to_numeric(train[TARGET], errors="raise").astype(int)

    if X.isna().all().any():
        raise ValueError("At least one rainfall feature is entirely missing.")
    if y.nunique() != 2:
        raise ValueError("Training target must contain both classes.")

    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("classifier", RandomForestClassifier(
            n_estimators=100,
            max_depth=18,
            min_samples_leaf=15,
            max_features="sqrt",
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=42,
        )),
    ])
    model.fit(X, y)

    cv = pd.read_csv(OUT / "cv_model_summary.csv")
    test = pd.read_csv(OUT / "test_model_metrics.csv")
    cv_row = cv.loc[cv["model"].eq("random_forest")]
    test_row = test.loc[test["model"].eq("random_forest")]

    if cv_row.empty or test_row.empty:
        raise ValueError("Random Forest evaluation row not found.")

    metadata = {
        "model_file": MODEL_PATH.name,
        "model_status": "experimental_not_for_operational_use",
        "algorithm": "RandomForestClassifier",
        "training_year": 2014,
        "training_rows": int(len(train)),
        "training_bridges": int(train["asset_id"].nunique()),
        "training_events": sorted(train["event_id"].astype(str).unique().tolist()),
        "features": FEATURES,
        "target": TARGET,
        "target_definition": (
            "Whether a bridge intersects a historical flood-event polygon; "
            "not structural damage or bridge failure."
        ),
        "preprocessing": "Median imputation",
        "random_state": 42,
        "cross_validation": {
            "mean_average_precision": float(cv_row.iloc[0]["mean_average_precision"]),
            "std_average_precision": float(cv_row.iloc[0]["std_average_precision"]),
        },
        "held_out_2015": {
            "average_precision": float(test_row.iloc[0]["average_precision"]),
            "roc_auc": float(test_row.iloc[0]["roc_auc"]),
        },
        "validation_warning": (
            "2015 holdout performance is weak. Do not treat predictions "
            "as reliable operational risk probabilities."
        ),
        "training_used_2015_data": False,
    }

    OUT.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("MODEL_SAVED:", MODEL_PATH)
    print("METADATA_SAVED:", META_PATH)
    print("TRAINING_ROWS:", len(train))
    print("TRAINING_EVENTS:", train["event_id"].nunique())
    print("CV_MEAN_AP:", metadata["cross_validation"]["mean_average_precision"])
    print("2015_HOLDOUT_AP:", metadata["held_out_2015"]["average_precision"])
    print("STATUS: EXPERIMENTAL — NOT CONNECTED TO LIVE RISK ENGINE")


if __name__ == "__main__":
    main()

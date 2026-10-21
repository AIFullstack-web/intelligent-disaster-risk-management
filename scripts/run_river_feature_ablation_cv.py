from pathlib import Path
import numpy as np
import pandas as pd
import sklearn

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold
from sklearn.metrics import average_precision_score, roc_auc_score, brier_score_loss

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "bridge_event_ml_features_with_river.csv"
OUT = ROOT / "artifacts" / "river_feature_ablation_cv"

TARGET = "flood_exposed"
GROUP = "event_id"

RAIN = [
    "rain_sum_3d_pre_event_mm",
    "rain_sum_7d_pre_event_mm",
    "rain_sum_14d_pre_event_mm",
    "rain_max_3d_pre_event_mm",
    "rain_max_7d_pre_event_mm",
    "rain_max_14d_pre_event_mm",
    "rain_mean_7d_pre_event_mm",
    "rain_mean_14d_pre_event_mm",
]

RIVER_NUMERIC = ["distance_to_waterway_km"]
RIVER_CATEGORICAL = ["nearest_waterway_type"]
RIVER = RIVER_NUMERIC + RIVER_CATEGORICAL

STATIC_NUMERIC = ["latitude", "longitude", "length_m", "lanes"]
STATIC_CATEGORICAL = ["highway", "surface"]
STATIC = STATIC_NUMERIC + STATIC_CATEGORICAL

FULL_WITHOUT_RIVER = STATIC + RAIN
FULL_WITH_RIVER = STATIC + RAIN + RIVER

SPECS = {
    "prior_baseline": {"kind": "prior", "features": []},
    "rainfall_logistic": {"kind": "logistic", "features": RAIN},
    "rainfall_random_forest": {"kind": "forest", "features": RAIN},
    "river_logistic": {"kind": "logistic", "features": RIVER},
    "river_random_forest": {"kind": "forest", "features": RIVER},
    "rainfall_river_logistic": {
        "kind": "logistic",
        "features": RAIN + RIVER,
    },
    "rainfall_river_random_forest": {
        "kind": "forest",
        "features": RAIN + RIVER,
    },
    "full_logistic_without_river": {
        "kind": "logistic",
        "features": FULL_WITHOUT_RIVER,
    },
    "full_random_forest_without_river": {
        "kind": "forest",
        "features": FULL_WITHOUT_RIVER,
    },
    "full_logistic_with_river": {
        "kind": "logistic",
        "features": FULL_WITH_RIVER,
    },
    "full_random_forest_with_river": {
        "kind": "forest",
        "features": FULL_WITH_RIVER,
    },
}

NUMERIC = set(STATIC_NUMERIC + RAIN + RIVER_NUMERIC)
CATEGORICAL = set(STATIC_CATEGORICAL + RIVER_CATEGORICAL)

def stop(message):
    raise ValueError(message)

def make_preprocessor(features, scale):
    numeric = [c for c in features if c in NUMERIC]
    categorical = [c for c in features if c in CATEGORICAL]
    transformers = []

    if numeric:
        steps = [("imputer", SimpleImputer(strategy="median"))]
        if scale:
            steps.append(("scaler", StandardScaler()))
        transformers.append(("numeric", Pipeline(steps), numeric))

    if categorical:
        categorical_pipe = Pipeline([
            ("imputer", SimpleImputer(
                strategy="constant",
                fill_value="__MISSING__",
            )),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ])
        transformers.append(
            ("categorical", categorical_pipe, categorical)
        )

    return ColumnTransformer(transformers, remainder="drop")

def make_model(name):
    spec = SPECS[name]

    if spec["kind"] == "prior":
        return None

    if spec["kind"] == "logistic":
        estimator = LogisticRegression(
            max_iter=500,
            class_weight="balanced",
            solver="liblinear",
            random_state=42,
        )
        scale = True
    else:
        estimator = RandomForestClassifier(
            n_estimators=100,
            max_depth=18,
            min_samples_leaf=15,
            max_features="sqrt",
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=42,
        )
        scale = False

    return Pipeline([
        ("preprocess", make_preprocessor(spec["features"], scale)),
        ("classifier", estimator),
    ])

def evaluate(y, probabilities):
    y = np.asarray(y, dtype=int)
    p = np.asarray(probabilities, dtype=float)
    prevalence = float(y.mean())

    positive_mean = float(p[y == 1].mean()) if (y == 1).any() else None
    negative_mean = float(p[y == 0].mean()) if (y == 0).any() else None

    return {
        "rows": len(y),
        "positives": int(y.sum()),
        "exposure_rate": prevalence,
        "average_precision": float(average_precision_score(y, p)),
        "ap_lift_over_prevalence": (
            float(average_precision_score(y, p) / prevalence)
            if prevalence else None
        ),
        "roc_auc": (
            float(roc_auc_score(y, p))
            if len(np.unique(y)) == 2 else None
        ),
        "brier_score": float(brier_score_loss(y, p)),
        "score_gap_positive_minus_negative": (
            positive_mean - negative_mean
            if positive_mean is not None and negative_mean is not None
            else None
        ),
    }

def main():
    if OUT.exists():
        stop(f"Refusing to overwrite existing folder: {OUT}")
    if not INPUT.exists():
        stop(f"Input dataset not found: {INPUT}")

    df = pd.read_csv(INPUT, low_memory=False)
    df["StartDate"] = pd.to_datetime(df["StartDate"], errors="raise")
    df = df[df["StartDate"].dt.year == 2014].copy().reset_index(drop=True)

    if df[GROUP].nunique() != 5:
        stop("Expected five 2014 flood events.")
    if df.duplicated(["asset_id", GROUP]).any():
        stop("Duplicate bridge-event records found.")

    for name, spec in SPECS.items():
        missing = set(spec["features"] + [TARGET, GROUP]) - set(df.columns)
        if missing:
            stop(f"{name}: missing columns {sorted(missing)}")

    if df[RAIN + RIVER_NUMERIC].isna().any().any():
        stop("Missing rainfall or river-distance predictors found.")

    if not np.isfinite(
        df[RAIN + RIVER_NUMERIC].to_numpy(dtype=float)
    ).all():
        stop("Non-finite rainfall or river-distance values found.")

    df["nearest_waterway_type"] = (
        df["nearest_waterway_type"].fillna("unknown").astype(str)
    )

    y = df[TARGET].astype(int)
    groups = df[GROUP]
    cv = GroupKFold(n_splits=5)
    rows = []

    print("SCIKIT_LEARN_VERSION:", sklearn.__version__)
    print("DATA_USED: 2014 events only")
    print("ROWS:", len(df))
    print("EVENTS:", groups.nunique())
    print("EXPOSURE_RATE_PCT:", round(100 * y.mean(), 2))
    print("MODEL_COUNT:", len(SPECS))
    print("VALIDATION: five-fold GroupKFold by event")
    print("2015 DATA USED FOR SELECTION: NO")

    for name, spec in SPECS.items():
        features = spec["features"]

        for fold, (fit_idx, val_idx) in enumerate(
            cv.split(df, y, groups=groups), start=1
        ):
            y_fit = y.iloc[fit_idx]
            y_val = y.iloc[val_idx]
            held_event = ";".join(sorted(groups.iloc[val_idx].unique()))

            if spec["kind"] == "prior":
                probabilities = np.full(len(val_idx), y_fit.mean())
            else:
                model = make_model(name)
                model.fit(df.iloc[fit_idx][features], y_fit)
                probabilities = model.predict_proba(
                    df.iloc[val_idx][features]
                )[:, 1]

            metrics = evaluate(y_val, probabilities)
            rows.append({
                "model": name,
                "fold": fold,
                "held_out_event": held_event,
                **metrics,
            })

            print(
                f"CV model={name} fold={fold} "
                f"event={held_event} "
                f"AP={metrics['average_precision']:.4f} "
                f"lift={metrics['ap_lift_over_prevalence']:.3f} "
                f"AUC={metrics['roc_auc']:.3f}"
            )

    folds = pd.DataFrame(rows)
    summary = folds.groupby("model").agg(
        mean_average_precision=("average_precision", "mean"),
        std_average_precision=("average_precision", "std"),
        mean_ap_lift=("ap_lift_over_prevalence", "mean"),
        mean_roc_auc=("roc_auc", "mean"),
        mean_brier_score=("brier_score", "mean"),
        mean_score_gap=("score_gap_positive_minus_negative", "mean"),
    ).reset_index()

    summary = summary.sort_values(
        ["mean_ap_lift", "mean_average_precision"],
        ascending=False,
    ).reset_index(drop=True)

    OUT.mkdir(parents=True, exist_ok=False)
    folds.to_csv(OUT / "cv_event_metrics.csv", index=False)
    summary.to_csv(OUT / "cv_model_summary.csv", index=False)

    print("\nRIVER FEATURE EXPERIMENT SUMMARY:")
    print(summary.to_string(index=False))
    print("\nFOLD RESULTS:", OUT / "cv_event_metrics.csv")
    print("SUMMARY:", OUT / "cv_model_summary.csv")
    print("OUTPUT_FILES_SAVED: PASSED")

if __name__ == "__main__":
    main()

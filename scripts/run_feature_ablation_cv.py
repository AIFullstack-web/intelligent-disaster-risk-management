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
INPUT = ROOT / "data" / "processed" / "bridge_event_ml_features.csv"
OUT = ROOT / "artifacts" / "feature_ablation_cv"

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

LOCATION = ["latitude", "longitude"]
STATIC_NUMERIC = LOCATION + ["length_m", "lanes"]
STATIC_CATEGORICAL = ["highway", "surface"]
STATIC = STATIC_NUMERIC + STATIC_CATEGORICAL
FULL = STATIC + RAIN

SPECS = {
    "prior_baseline": {"kind": "prior", "features": []},
    "location_logistic": {"kind": "logistic", "features": LOCATION},
    "static_logistic": {"kind": "logistic", "features": STATIC},
    "rainfall_logistic": {"kind": "logistic", "features": RAIN},
    "full_logistic": {"kind": "logistic", "features": FULL},
    "rainfall_random_forest": {"kind": "forest", "features": RAIN},
    "full_random_forest": {"kind": "forest", "features": FULL},
}

def fail(message):
    raise ValueError(message)

def make_preprocessor(features, scale):
    numeric = [c for c in features if c in STATIC_NUMERIC + RAIN]
    categorical = [c for c in features if c in STATIC_CATEGORICAL]
    transformers = []

    if numeric:
        steps = [("imputer", SimpleImputer(strategy="median"))]
        if scale:
            steps.append(("scaler", StandardScaler()))
        transformers.append(("numeric", Pipeline(steps), numeric))

    if categorical:
        cat_pipe = Pipeline([
            ("imputer", SimpleImputer(
                strategy="constant", fill_value="__MISSING__"
            )),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ])
        transformers.append(("categorical", cat_pipe, categorical))

    return ColumnTransformer(transformers, remainder="drop")

def make_model(name):
    spec = SPECS[name]
    features = spec["features"]
    kind = spec["kind"]

    if kind == "prior":
        return None

    if kind == "logistic":
        return Pipeline([
            ("preprocess", make_preprocessor(features, scale=True)),
            ("classifier", LogisticRegression(
                max_iter=500,
                class_weight="balanced",
                solver="liblinear",
                random_state=42,
            )),
        ])

    return Pipeline([
        ("preprocess", make_preprocessor(features, scale=False)),
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

def metric_row(y, probability):
    y = np.asarray(y, dtype=int)
    probability = np.asarray(probability, dtype=float)
    prevalence = float(y.mean())

    positives = probability[y == 1]
    negatives = probability[y == 0]
    gap = (
        float(positives.mean() - negatives.mean())
        if len(positives) and len(negatives)
        else None
    )

    return {
        "rows": len(y),
        "positives": int(y.sum()),
        "exposure_rate": prevalence,
        "average_precision": float(average_precision_score(y, probability)),
        "ap_lift_over_prevalence": (
            float(average_precision_score(y, probability) / prevalence)
            if prevalence > 0 else None
        ),
        "roc_auc": (
            float(roc_auc_score(y, probability))
            if len(np.unique(y)) == 2 else None
        ),
        "brier_score": float(brier_score_loss(y, probability)),
        "mean_score_gap_positive_minus_negative": gap,
    }

def main():
    if OUT.exists():
        fail(f"Refusing to overwrite existing folder: {OUT}")
    if not INPUT.exists():
        fail(f"Dataset not found: {INPUT}")

    df = pd.read_csv(INPUT, low_memory=False)
    df["StartDate"] = pd.to_datetime(df["StartDate"], errors="raise")
    df = df[df["StartDate"].dt.year == 2014].copy()
    df.reset_index(drop=True, inplace=True)

    if df[GROUP].nunique() != 5:
        fail("Expected five 2014 events.")
    if df.duplicated(["asset_id", GROUP]).any():
        fail("Duplicate bridge-event rows found.")

    required = set(FULL + [TARGET, GROUP])
    if not required.issubset(df.columns):
        fail(f"Missing columns: {sorted(required - set(df.columns))}")

    if df[RAIN].isna().any().any():
        fail("Missing rainfall features found.")

    y = df[TARGET].astype(int)
    groups = df[GROUP]
    cv = GroupKFold(n_splits=5)
    rows = []

    print("SCIKIT_LEARN_VERSION:", sklearn.__version__)
    print("DATA_USED: 2014 events only")
    print("ROWS:", len(df))
    print("EVENTS:", df[GROUP].nunique())
    print("EXPOSURE_RATE_PCT:", round(100 * y.mean(), 2))
    print("MODELS:", ", ".join(SPECS))
    print("VALIDATION: five folds grouped by event")
    print("2015 DATA: NOT USED")

    for name, spec in SPECS.items():
        features = spec["features"]
        x = df[features] if features else None

        for fold, (fit_idx, val_idx) in enumerate(
            cv.split(df, y, groups=groups), start=1
        ):
            y_fit = y.iloc[fit_idx]
            y_val = y.iloc[val_idx]
            held_event = ";".join(sorted(groups.iloc[val_idx].unique()))

            if spec["kind"] == "prior":
                probability = np.full(len(val_idx), y_fit.mean())
            else:
                model = make_model(name)
                model.fit(x.iloc[fit_idx], y_fit)
                probability = model.predict_proba(x.iloc[val_idx])[:, 1]

            metrics = metric_row(y_val, probability)
            rows.append({
                "model": name,
                "fold": fold,
                "held_out_event": held_event,
                **metrics,
            })

            print(
                f"CV model={name} fold={fold} event={held_event} "
                f"AP={metrics['average_precision']:.4f} "
                f"prevalence={metrics['exposure_rate']:.4f} "
                f"lift={metrics['ap_lift_over_prevalence']:.3f} "
                f"AUC={metrics['roc_auc']}"
            )

    folds = pd.DataFrame(rows)
    summary = folds.groupby("model").agg(
        mean_average_precision=("average_precision", "mean"),
        std_average_precision=("average_precision", "std"),
        mean_ap_lift=("ap_lift_over_prevalence", "mean"),
        mean_roc_auc=("roc_auc", "mean"),
        mean_brier_score=("brier_score", "mean"),
        mean_score_gap=("mean_score_gap_positive_minus_negative", "mean"),
    ).reset_index()

    summary = summary.sort_values(
        ["mean_ap_lift", "mean_average_precision"],
        ascending=False
    )

    OUT.mkdir(parents=True, exist_ok=False)
    folds.to_csv(OUT / "cv_event_metrics.csv", index=False)
    summary.to_csv(OUT / "cv_model_summary.csv", index=False)

    print("\nFEATURE ABLATION SUMMARY:")
    print(summary.to_string(index=False))
    print("\nFOLD RESULTS:", OUT / "cv_event_metrics.csv")
    print("SUMMARY:", OUT / "cv_model_summary.csv")
    print("OUTPUT_FILES_SAVED: PASSED")

if __name__ == "__main__":
    main()

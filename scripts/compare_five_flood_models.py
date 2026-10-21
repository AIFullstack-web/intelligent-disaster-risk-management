import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import BaggingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score, brier_score_loss
from sklearn.model_selection import GroupKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "bridge_event_ml_features.csv"
OUT = ROOT / "artifacts" / "five_algorithm_comparison"

TARGET = "flood_exposed"
GROUP = "event_id"
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

MODEL_NAMES = [
    "random_forest",
    "bagging",
    "svm_linear",
    "knn",
    "glm_logistic",
]


def make_model(name):
    steps = [("imputer", SimpleImputer(strategy="median"))]

    if name in {"svm_linear", "knn", "glm_logistic"}:
        steps.append(("scaler", StandardScaler()))

    preprocess = Pipeline(steps)

    if name == "random_forest":
        estimator = RandomForestClassifier(
            n_estimators=100,
            max_depth=18,
            min_samples_leaf=15,
            max_features="sqrt",
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=42,
        )
    elif name == "bagging":
        tree = DecisionTreeClassifier(
            max_depth=18,
            min_samples_leaf=15,
            class_weight="balanced",
            random_state=42,
        )
        estimator = BaggingClassifier(
            estimator=tree,
            n_estimators=100,
            max_samples=0.8,
            n_jobs=-1,
            random_state=42,
        )
    elif name == "svm_linear":
        estimator = LinearSVC(
            C=1.0,
            class_weight="balanced",
            max_iter=5000,
            random_state=42,
        )
    elif name == "knn":
        estimator = KNeighborsClassifier(
            n_neighbors=25,
            weights="distance",
            n_jobs=-1,
        )
    elif name == "glm_logistic":
        estimator = LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            solver="liblinear",
            random_state=42,
        )
    else:
        raise ValueError(f"Unknown model: {name}")

    return Pipeline([
        ("preprocess", preprocess),
        ("classifier", estimator),
    ])


def get_scores(model, features):
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(features)[:, 1]
        return probabilities, probabilities

    scores = model.decision_function(features)
    return np.asarray(scores), None


def calculate_metrics(y_true, scores, probabilities=None):
    y = np.asarray(y_true, dtype=int)
    scores = np.asarray(scores, dtype=float)

    auc = (
        roc_auc_score(y, scores)
        if len(np.unique(y)) == 2
        else np.nan
    )

    top_count = max(1, math.ceil(len(y) * 0.10))
    top_indices = np.argsort(scores)[-top_count:]
    positives = int(y.sum())

    return {
        "samples": int(len(y)),
        "positives": positives,
        "positive_rate": float(y.mean()),
        "average_precision": float(average_precision_score(y, scores)),
        "roc_auc": float(auc),
        "brier_score": (
            float(brier_score_loss(y, probabilities))
            if probabilities is not None
            else np.nan
        ),
        "precision_at_top_10pct": float(y[top_indices].mean()),
        "recall_at_top_10pct": (
            float(y[top_indices].sum() / positives)
            if positives
            else np.nan
        ),
    }


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Feature dataset not found: {INPUT}")

    if OUT.exists() and any(OUT.iterdir()):
        raise FileExistsError(
            f"Output folder already contains files: {OUT}. "
            "Review them before running again."
        )

    df = pd.read_csv(INPUT, low_memory=False)

    required = set(
        FEATURES + [TARGET, GROUP, DATE, "asset_id", "EndDate"]
    )
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    if df.duplicated(["asset_id", GROUP]).any():
        raise ValueError("Duplicate bridge-event rows were found.")

    df[DATE] = pd.to_datetime(df[DATE], errors="raise")
    df[TARGET] = pd.to_numeric(df[TARGET], errors="raise").astype(int)

    if not set(df[TARGET].unique()).issubset({0, 1}):
        raise ValueError("The target must contain only 0 and 1.")

    years = set(df[DATE].dt.year.unique())
    if years != {2014, 2015}:
        raise ValueError(
            f"Expected data from 2014 and 2015 only; found {sorted(years)}"
        )

    X = df[FEATURES].apply(pd.to_numeric, errors="coerce")
    if X.isna().all().any():
        raise ValueError("At least one rainfall feature is entirely missing.")

    train_mask = df[DATE].dt.year.eq(2014)
    test_mask = df[DATE].dt.year.eq(2015)

    train = df.loc[train_mask].reset_index(drop=True)
    test = df.loc[test_mask].reset_index(drop=True)
    X_train = X.loc[train_mask].reset_index(drop=True)
    X_test = X.loc[test_mask].reset_index(drop=True)
    y_train = train[TARGET]
    y_test = test[TARGET]

    event_count = train[GROUP].nunique()
    if event_count < 2:
        raise ValueError("At least two training events are required.")

    cv = GroupKFold(n_splits=event_count)
    cv_rows = []

    print("TRAIN_ROWS:", len(train))
    print("TEST_ROWS:", len(test))
    print("TRAIN_EVENTS:", event_count)
    print("TRAIN_POSITIVE_RATE_PCT:", round(100 * y_train.mean(), 2))
    print("TEST_POSITIVE_RATE_PCT:", round(100 * y_test.mean(), 2))
    print("FEATURE_SET: eight rainfall features")
    print("VALIDATION: GroupKFold grouped by 2014 flood event")

    for name in MODEL_NAMES:
        for fold, (fit_idx, val_idx) in enumerate(
            cv.split(X_train, y_train, groups=train[GROUP]),
            start=1,
        ):
            model = make_model(name)
            model.fit(X_train.iloc[fit_idx], y_train.iloc[fit_idx])

            scores, probabilities = get_scores(
                model, X_train.iloc[val_idx]
            )
            metrics = calculate_metrics(
                y_train.iloc[val_idx], scores, probabilities
            )

            held_events = sorted(
                train.iloc[val_idx][GROUP].astype(str).unique()
            )
            cv_rows.append({
                "model": name,
                "fold": fold,
                "validation_events": ";".join(held_events),
                **metrics,
            })

            print(
                f"CV model={name} fold={fold} "
                f"events={';'.join(held_events)} "
                f"AP={metrics['average_precision']:.4f}"
            )

    cv_df = pd.DataFrame(cv_rows)
    summary = cv_df.groupby("model").agg(
        mean_average_precision=("average_precision", "mean"),
        std_average_precision=("average_precision", "std"),
        mean_roc_auc=("roc_auc", "mean"),
        mean_brier_score=("brier_score", "mean"),
        mean_precision_at_top_10pct=("precision_at_top_10pct", "mean"),
        mean_recall_at_top_10pct=("recall_at_top_10pct", "mean"),
    ).reset_index().sort_values(
        "mean_average_precision", ascending=False
    )

    metadata_cols = [
        c for c in
        ["asset_id", "osm_id", "event_id", "StartDate", "EndDate", TARGET]
        if c in test.columns
    ]
    predictions = test[metadata_cols].copy()
    test_metric_rows = []
    event_metric_rows = []

    for name in MODEL_NAMES:
        model = make_model(name)
        model.fit(X_train, y_train)
        scores, probabilities = get_scores(model, X_test)

        overall = calculate_metrics(y_test, scores, probabilities)
        test_metric_rows.append({"model": name, **overall})

        predictions[f"{name}_score"] = scores
        if probabilities is not None:
            predictions[f"{name}_probability"] = probabilities

        for event_id in sorted(test[GROUP].astype(str).unique()):
            event_mask = test[GROUP].astype(str).eq(event_id).to_numpy()
            event_metrics = calculate_metrics(
                y_test.to_numpy()[event_mask],
                scores[event_mask],
                probabilities[event_mask]
                if probabilities is not None
                else None,
            )
            event_metric_rows.append({
                "model": name,
                "event_id": event_id,
                **event_metrics,
            })

        print(
            f"2015 TEST model={name} "
            f"AP={overall['average_precision']:.4f} "
            f"AUC={overall['roc_auc']:.4f}"
        )

    OUT.mkdir(parents=True, exist_ok=True)
    cv_df.to_csv(OUT / "cv_fold_metrics.csv", index=False)
    summary.to_csv(OUT / "cv_model_summary.csv", index=False)
    pd.DataFrame(test_metric_rows).to_csv(
        OUT / "test_model_metrics.csv", index=False
    )
    pd.DataFrame(event_metric_rows).to_csv(
        OUT / "test_event_metrics.csv", index=False
    )
    predictions.to_csv(OUT / "test_predictions.csv", index=False)

    metadata = {
        "input_dataset": str(INPUT.relative_to(ROOT)),
        "target": TARGET,
        "target_definition": (
            "Historical bridge intersection with a flood-event polygon; "
            "not structural damage or bridge failure."
        ),
        "features": FEATURES,
        "models": MODEL_NAMES,
        "training_year": 2014,
        "holdout_year": 2015,
        "cross_validation": f"{event_count}-fold GroupKFold grouped by event_id",
        "svm_note": (
            "Linear SVM uses decision scores for ranking metrics. "
            "Brier score is not reported for SVM because scores are not "
            "calibrated probabilities."
        ),
        "selection_note": (
            "This script reports the comparison and does not automatically "
            "replace the current production model."
        ),
        "random_state": 42,
    }
    with open(OUT / "run_metadata.json", "w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2)

    print("\nCROSS-VALIDATION SUMMARY:")
    print(summary.to_string(index=False))
    print("\nOUTPUT_FOLDER:", OUT)
    print("MODEL COMPARISON COMPLETED.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise

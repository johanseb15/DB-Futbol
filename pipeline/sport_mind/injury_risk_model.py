"""Injury risk model utilities for Sport-Mind AI MVP.

Model type: RandomForestClassifier (scikit-learn)
Target: probability of muscle injury in the next 7 days.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "high_intensity_distance_m",
    "sleep_hours",
    "cortisol_level",
    "weekly_workload",
]
TARGET_COLUMN = "muscle_injury_next_7d"


@dataclass
class InjuryModelArtifacts:
    model: object
    feature_columns: Sequence[str]
    train_rows: int
    positive_rate: float


def _require_sklearn():
    try:
        from sklearn.ensemble import RandomForestClassifier  # noqa: F401
        from sklearn.model_selection import train_test_split  # noqa: F401
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "scikit-learn is required for injury model training. "
            "Install with: pip install -r requirements_ai.txt"
        ) from exc


def build_feature_frame(rows: Iterable[dict]) -> pd.DataFrame:
    """Normalize raw rows into training frame."""
    df = pd.DataFrame(rows)
    missing = [col for col in FEATURE_COLUMNS + [TARGET_COLUMN] if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Lightweight cleaning for MVP.
    for col in FEATURE_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df[TARGET_COLUMN] = df[TARGET_COLUMN].astype("Int64")
    df = df.dropna(subset=FEATURE_COLUMNS + [TARGET_COLUMN])
    df[TARGET_COLUMN] = df[TARGET_COLUMN].astype(int)
    return df


def train_random_forest(rows: Iterable[dict], random_state: int = 42) -> InjuryModelArtifacts:
    """Train RandomForest on injury data and return model artifacts."""
    _require_sklearn()

    from sklearn.ensemble import RandomForestClassifier

    df = build_feature_frame(rows)
    if df.empty:
        raise ValueError("No valid rows after preprocessing.")

    x = df[FEATURE_COLUMNS].to_numpy(dtype=float)
    y = df[TARGET_COLUMN].to_numpy(dtype=int)

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=5,
        random_state=random_state,
        class_weight="balanced",
    )
    model.fit(x, y)

    return InjuryModelArtifacts(
        model=model,
        feature_columns=FEATURE_COLUMNS,
        train_rows=len(df),
        positive_rate=float(np.mean(y)),
    )


def predict_injury_probability(
    artifacts: InjuryModelArtifacts,
    high_intensity_distance_m: float,
    sleep_hours: float,
    cortisol_level: float,
    weekly_workload: float,
) -> float:
    """Predict injury probability for one sample."""
    sample = np.array(
        [[high_intensity_distance_m, sleep_hours, cortisol_level, weekly_workload]],
        dtype=float,
    )
    proba = artifacts.model.predict_proba(sample)[0][1]
    return float(proba)


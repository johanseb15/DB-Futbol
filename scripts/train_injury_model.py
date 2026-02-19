"""Train Sport-Mind injury model from CSV.

Example:
  python scripts/train_injury_model.py --csv data/injury_training.csv --out models/injury_rf.joblib
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from pipeline.sport_mind.injury_risk_model import train_random_forest


def _require_joblib():
    try:
        import joblib  # noqa: F401
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "joblib is required to persist model artifacts. "
            "Install with: pip install -r requirements_ai.txt"
        ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Train injury risk model")
    parser.add_argument("--csv", required=True, help="Path to training CSV")
    parser.add_argument("--out", default="models/injury_rf.joblib", help="Output artifact path")
    args = parser.parse_args()

    _require_joblib()
    import joblib

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    rows = pd.read_csv(csv_path).to_dict(orient="records")
    artifacts = train_random_forest(rows)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": artifacts.model,
            "feature_columns": list(artifacts.feature_columns),
            "train_rows": artifacts.train_rows,
            "positive_rate": artifacts.positive_rate,
        },
        out_path,
    )

    print("model_saved")
    print(f"path={out_path}")
    print(f"train_rows={artifacts.train_rows}")
    print(f"positive_rate={artifacts.positive_rate:.4f}")


if __name__ == "__main__":
    main()


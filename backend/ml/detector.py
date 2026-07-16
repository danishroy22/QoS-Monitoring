"""Isolation Forest anomaly detector with train / load / predict helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

from .features import FEATURE_NAMES, MODEL_NAME, extract_feature_matrix

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
DEFAULT_MODEL_PATH = ARTIFACTS_DIR / f"{MODEL_NAME}.joblib"
DEFAULT_META_PATH = ARTIFACTS_DIR / f"{MODEL_NAME}_meta.json"


@dataclass
class DetectionResult:
    """Score and flag for one measurement."""

    is_anomaly: bool
    anomaly_score: float
    raw_prediction: int  # -1 anomaly, 1 normal (sklearn convention)


class AnomalyDetector:
    """Wrapper around scikit-learn IsolationForest for QoS samples."""

    def __init__(self, model: IsolationForest | None = None, meta: dict | None = None) -> None:
        self.model = model
        self.meta = meta or {}

    @property
    def is_ready(self) -> bool:
        return self.model is not None

    @classmethod
    def train(
        cls,
        rows: Sequence[Any],
        *,
        contamination: float = 0.08,
        n_estimators: int = 200,
        random_state: int = 42,
    ) -> "AnomalyDetector":
        """Fit Isolation Forest on the provided measurement rows."""
        matrix = extract_feature_matrix(rows)
        if matrix.shape[0] < 20:
            raise ValueError("Need at least 20 samples to train the anomaly detector.")

        model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=random_state,
            n_jobs=-1,
        )
        model.fit(matrix)
        meta = {
            "model_name": MODEL_NAME,
            "n_samples": int(matrix.shape[0]),
            "n_features": int(matrix.shape[1]),
            "feature_names": FEATURE_NAMES,
            "contamination": contamination,
            "n_estimators": n_estimators,
            "random_state": random_state,
        }
        return cls(model=model, meta=meta)

    def save(self, path: Path | None = None, meta_path: Path | None = None) -> Path:
        if self.model is None:
            raise RuntimeError("No trained model to save.")
        path = path or DEFAULT_MODEL_PATH
        meta_path = meta_path or DEFAULT_META_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, path)
        meta_path.write_text(json.dumps(self.meta, indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path | None = None, meta_path: Path | None = None) -> "AnomalyDetector":
        path = path or DEFAULT_MODEL_PATH
        meta_path = meta_path or DEFAULT_META_PATH
        if not path.exists():
            raise FileNotFoundError(
                f"Model artefact not found at {path}. "
                "Train one with: python -m backend.ml.train"
            )
        model = joblib.load(path)
        meta: dict = {}
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return cls(model=model, meta=meta)

    def predict_one(self, row: Any) -> DetectionResult:
        return self.predict_many([row])[0]

    def predict_many(self, rows: Sequence[Any]) -> list[DetectionResult]:
        if self.model is None:
            raise RuntimeError("Detector has no loaded model.")
        if not rows:
            return []
        matrix = extract_feature_matrix(rows)
        preds = self.model.predict(matrix)
        scores = self.model.decision_function(matrix)
        results: list[DetectionResult] = []
        for pred, score in zip(preds, scores, strict=True):
            results.append(
                DetectionResult(
                    is_anomaly=bool(pred == -1),
                    anomaly_score=float(score),
                    raw_prediction=int(pred),
                )
            )
        return results


# Re-export for convenience
__all__ = ["AnomalyDetector", "DetectionResult", "MODEL_NAME", "DEFAULT_MODEL_PATH"]

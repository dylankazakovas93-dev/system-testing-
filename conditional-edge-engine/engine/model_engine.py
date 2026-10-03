"""Frozen model bank v1: RIDGE, SPLINE (additive spline + ridge), XGB. No tuning, no search.

All three consume the ENTIRE 56-feature bank. day_of_week is one-hot encoded with fixed
categories (MODEL_BANK.yaml) and is never splined. Hyperparameters are read from the frozen
YAML at construction time, so the YAML hash freezes the models.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import SplineTransformer, StandardScaler
from xgboost import XGBRegressor

from engine.common import EngineError, Frozen
from engine.feature_engine import feature_names

DOW = "day_of_week"


class FrozenModel:
    """fit(X_df, y) / predict(X_df) over the frozen feature columns."""

    def __init__(self, name: str, frozen: Frozen):
        if name not in frozen.model_bank["models"]:
            raise EngineError(f"unknown model {name!r}; the frozen bank has {list(frozen.model_bank['models'])}")
        self.name = name
        self.spec = frozen.model_bank["models"][name]
        self.categories = list(frozen.model_bank["day_of_week_categories"])
        self.target_transform = frozen.model_bank.get("target_transform", "none")
        if self.target_transform not in ("none", "train_only_standardization"):
            raise EngineError(f"unknown target_transform {self.target_transform!r}")
        self.names = feature_names(frozen)
        self.cont = [n for n in self.names if n != DOW]
        self._fitted = False

    # -- design matrices -------------------------------------------------------------------
    def _onehot(self, X: pd.DataFrame) -> np.ndarray:
        dow = X[DOW].to_numpy("float64")
        if not np.isfinite(dow).all():
            raise EngineError("day_of_week must be finite for modelling")
        return (dow[:, None] == np.asarray(self.categories, dtype=float)[None, :]).astype("float64")

    def _cont(self, X: pd.DataFrame) -> np.ndarray:
        block = X[self.cont].to_numpy("float64")
        if not np.isfinite(block).all():
            raise EngineError("non-finite feature reached the model (no imputation is performed)")
        return block

    def fit(self, X: pd.DataFrame, y) -> "FrozenModel":
        y = np.asarray(y, dtype="float64")
        if len(X) != len(y) or not np.isfinite(y).all():
            raise EngineError("training labels must be finite and aligned")
        cont, hot = self._cont(X), self._onehot(X)
        kind, p = self.spec["kind"], self.spec["params"]
        self.y_mean, self.y_sd = 0.0, 1.0
        if self.target_transform == "train_only_standardization":
            self.y_mean = float(y.mean())
            sd = float(y.std())
            self.y_sd = sd if sd > 0 else 1.0
            y = (y - self.y_mean) / self.y_sd                               # TRAIN-ONLY statistics
        if kind == "ridge":
            self.scaler = StandardScaler().fit(cont)                      # train-only standardization
            design = np.hstack([self.scaler.transform(cont), hot])
            self.est = Ridge(alpha=p["alpha"], fit_intercept=p["fit_intercept"]).fit(design, y)
        elif kind == "additive_spline_ridge":
            s = self.spec["spline"]
            self.spl = SplineTransformer(degree=s["degree"], n_knots=s["n_knots"], knots=s["knots"],
                                         include_bias=s["include_bias"]).fit(cont)   # knots from TRAIN only
            design = np.hstack([self.spl.transform(cont), hot])
            self.est = Ridge(alpha=p["alpha"], fit_intercept=p["fit_intercept"]).fit(design, y)
        elif kind == "xgboost_regressor":
            design = np.hstack([cont, hot])
            self.est = XGBRegressor(**p, n_jobs=1, verbosity=0).fit(design, y)   # no early stopping
        else:
            raise EngineError(f"unknown model kind {kind}")
        self._fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self._fitted:
            raise EngineError("model not fitted")
        cont, hot = self._cont(X), self._onehot(X)
        kind = self.spec["kind"]
        if kind == "ridge":
            design = np.hstack([self.scaler.transform(cont), hot])
        elif kind == "additive_spline_ridge":
            design = np.hstack([self.spl.transform(cont), hot])
        else:
            design = np.hstack([cont, hot])
        raw = np.asarray(self.est.predict(design), dtype="float64")
        return raw * self.y_sd + self.y_mean                               # back to raw target units

    def feature_coefficients(self) -> dict[str, float]:
        """DIAGNOSTIC ONLY: signed standardized Ridge coefficients (None for non-Ridge models)."""
        if self.spec["kind"] != "ridge":
            return {}
        w = self.est.coef_
        return dict(zip(self.cont + [DOW], list(w[:len(self.cont)]) + [float(np.abs(w[len(self.cont):]).sum())]))

    def feature_importance(self) -> dict[str, float]:
        """DIAGNOSTIC ONLY (never used for selection or feature subsetting)."""
        ncat = len(self.categories)
        kind = self.spec["kind"]
        if kind == "ridge":
            w = np.abs(self.est.coef_)
            per = list(w[:len(self.cont)]) + [float(w[len(self.cont):].sum())]
        elif kind == "additive_spline_ridge":
            w = np.abs(self.est.coef_)
            k = self.spl.n_features_out_ // len(self.cont)
            per = [float(w[i * k:(i + 1) * k].sum()) for i in range(len(self.cont))]
            per.append(float(w[self.spl.n_features_out_:].sum()))
        else:
            imp = np.asarray(self.est.feature_importances_, dtype=float)
            per = list(imp[:len(self.cont)]) + [float(imp[len(self.cont):].sum())]
        return dict(zip(self.cont + [DOW], per))


def make_model_factory(name: str, frozen: Frozen):
    return lambda: FrozenModel(name, frozen)

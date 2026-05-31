from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class FactorWeights:
    momentum: float = 0.40
    value: float = 0.30
    quality: float = 0.30


def cross_sectional_zscore(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    """Winsorize and z-score a cross-section without leaking future data."""

    numeric = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)
    if not higher_is_better:
        numeric = -numeric
    if numeric.dropna().empty:
        return pd.Series(0.0, index=series.index)
    clipped = numeric.clip(numeric.quantile(0.05), numeric.quantile(0.95))
    std = clipped.std(ddof=0)
    if pd.isna(std) or std == 0:
        return pd.Series(0.0, index=series.index)
    return ((clipped - clipped.mean()) / std).fillna(0.0)


class FactorEngine:
    """Computes Value, 12-1 Momentum, Quality and blended scores."""

    def __init__(self, weights: FactorWeights | None = None) -> None:
        self.weights = weights or FactorWeights()

    def compute_momentum(self, prices: pd.DataFrame, as_of: date) -> pd.Series:
        if prices.empty:
            return pd.Series(dtype=float)
        frame = prices[prices["date"] <= as_of].copy()
        frame["date"] = pd.to_datetime(frame["date"])
        pivot = frame.pivot_table(index="date", columns="symbol", values="close", aggfunc="last").sort_index()
        end = pivot.ffill().iloc[-1]
        one_month_cutoff = pd.Timestamp(as_of) - pd.DateOffset(months=1)
        twelve_month_cutoff = pd.Timestamp(as_of) - pd.DateOffset(months=12)
        if pivot[pivot.index <= one_month_cutoff].empty or pivot[pivot.index <= twelve_month_cutoff].empty:
            return pd.Series(0.0, index=end.index)
        price_1m = pivot[pivot.index <= one_month_cutoff].ffill().iloc[-1]
        price_12m = pivot[pivot.index <= twelve_month_cutoff].ffill().iloc[-1]
        raw = (price_1m / price_12m) - 1.0
        return cross_sectional_zscore(raw)

    def compute_value(self, fundamentals: pd.DataFrame) -> pd.Series:
        if fundamentals.empty:
            return pd.Series(dtype=float)
        frame = fundamentals.set_index("symbol")
        scores = []
        for column in ["per", "pbr", "psr", "ev_ebitda"]:
            inverse = 1.0 / pd.to_numeric(frame[column], errors="coerce")
            scores.append(cross_sectional_zscore(inverse))
        return pd.concat(scores, axis=1).mean(axis=1)

    def compute_quality(self, fundamentals: pd.DataFrame) -> pd.Series:
        if fundamentals.empty:
            return pd.Series(dtype=float)
        frame = fundamentals.set_index("symbol")
        components = [
            cross_sectional_zscore(frame["roe"]),
            cross_sectional_zscore(frame["roa"]),
            cross_sectional_zscore(frame["operating_margin"]),
            cross_sectional_zscore(frame["debt_ratio"], higher_is_better=False),
        ]
        return pd.concat(components, axis=1).mean(axis=1)

    def score(self, prices: pd.DataFrame, fundamentals: pd.DataFrame, as_of: date) -> pd.DataFrame:
        momentum = self.compute_momentum(prices, as_of)
        value = self.compute_value(fundamentals)
        quality = self.compute_quality(fundamentals)
        symbols = sorted(set(momentum.index) | set(value.index) | set(quality.index))
        result = pd.DataFrame(index=symbols)
        result["momentum"] = momentum.reindex(symbols).fillna(0.0)
        result["value"] = value.reindex(symbols).fillna(0.0)
        result["quality"] = quality.reindex(symbols).fillna(0.0)
        result["score"] = (
            self.weights.momentum * result["momentum"]
            + self.weights.value * result["value"]
            + self.weights.quality * result["quality"]
        )
        return result.sort_values("score", ascending=False).reset_index(names="symbol")

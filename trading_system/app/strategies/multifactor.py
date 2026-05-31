from datetime import date

import pandas as pd

from trading_system.app.factors.engine import FactorEngine, FactorWeights
from trading_system.app.strategies.base import BaseStrategy


class MultiFactorStrategy(BaseStrategy):
    """Korea equity Value + Momentum + Quality strategy."""

    def __init__(self, top_n: int = 20, weights: FactorWeights | None = None) -> None:
        self.top_n = top_n
        self.factor_engine = FactorEngine(weights)

    def generate_signals(self, as_of: date, prices: pd.DataFrame, fundamentals: pd.DataFrame) -> pd.DataFrame:
        scores = self.factor_engine.score(prices, fundamentals, as_of)
        selected = scores.head(self.top_n).copy()
        if selected.empty:
            selected["target_weight"] = []
            return selected
        selected["target_weight"] = min(0.05, 1.0 / self.top_n)
        return selected[["symbol", "target_weight", "score", "momentum", "value", "quality"]]

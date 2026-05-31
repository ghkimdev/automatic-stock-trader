from dataclasses import dataclass
from datetime import date

import pandas as pd

from trading_system.app.backtest.engine import BacktestEngine


@dataclass(frozen=True)
class WalkForwardWindow:
    train_start: date
    train_end: date
    test_start: date
    test_end: date


class WalkForwardEngine:
    """Runs 3-year train / 1-year test windows and parameter robustness sweeps."""

    def __init__(self, backtest_engine: BacktestEngine) -> None:
        self.backtest_engine = backtest_engine

    def windows(self, start_year: int, end_year: int, train_years: int = 3, test_years: int = 1) -> list[WalkForwardWindow]:
        result: list[WalkForwardWindow] = []
        for train_start in range(start_year, end_year - train_years - test_years + 2):
            train_end = train_start + train_years - 1
            test_start = train_end + 1
            test_end = test_start + test_years - 1
            result.append(WalkForwardWindow(date(train_start, 1, 1), date(train_end, 12, 31), date(test_start, 1, 1), date(test_end, 12, 31)))
        return result

    def run(self, prices: pd.DataFrame, fundamentals: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
        rows = []
        for window in self.windows(start_year, end_year):
            result = self.backtest_engine.run(prices, fundamentals, window.test_start, window.test_end)
            rows.append({"train_start": window.train_start, "train_end": window.train_end, "test_start": window.test_start, "test_end": window.test_end, **result["metrics"]})
        return pd.DataFrame(rows)

    def parameter_sweep(self, prices: pd.DataFrame, fundamentals: pd.DataFrame, start: date, end: date, momentum_weights: list[float]) -> pd.DataFrame:
        rows = []
        for weight in momentum_weights:
            remaining = 1.0 - weight
            strategy = self.backtest_engine.strategy
            if hasattr(strategy, "factor_engine"):
                strategy.factor_engine.weights = strategy.factor_engine.weights.__class__(momentum=weight, value=remaining / 2, quality=remaining / 2)
            result = self.backtest_engine.run(prices, fundamentals, start, end)
            rows.append({"momentum_weight": weight, **result["metrics"]})
        return pd.DataFrame(rows)

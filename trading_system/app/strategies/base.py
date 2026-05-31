from abc import ABC, abstractmethod
from datetime import date

import pandas as pd


class BaseStrategy(ABC):
    """Plugin contract for strategies; new strategies subclass this without changing callers."""

    @abstractmethod
    def generate_signals(self, as_of: date, prices: pd.DataFrame, fundamentals: pd.DataFrame) -> pd.DataFrame:
        """Return a DataFrame with symbol, target_weight, and score columns."""

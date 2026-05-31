from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class RiskDecision:
    allow_new_positions: bool
    forced_exit_symbols: list[str]
    reason: str


class RiskEngine:
    """Applies position stops and KOSPI200 market-risk filter."""

    def __init__(self, stop_loss: float = -0.10, trailing_stop: float = -0.15) -> None:
        self.stop_loss = stop_loss
        self.trailing_stop = trailing_stop

    def market_filter(self, kospi200_prices: pd.DataFrame) -> bool:
        if len(kospi200_prices) < 200:
            return True
        close = kospi200_prices.sort_values("date")["close"]
        ma50 = close.rolling(50).mean().iloc[-1]
        ma200 = close.rolling(200).mean().iloc[-1]
        return bool(ma50 >= ma200)

    def evaluate(
        self,
        positions: dict[str, tuple[int, float, float]],
        latest_prices: dict[str, float],
        kospi200_prices: pd.DataFrame,
    ) -> RiskDecision:
        forced: list[str] = []
        for symbol, (_, avg_price, peak_price) in positions.items():
            latest = latest_prices.get(symbol)
            if latest is None or avg_price <= 0 or peak_price <= 0:
                continue
            if latest / avg_price - 1.0 <= self.stop_loss:
                forced.append(symbol)
            elif latest / peak_price - 1.0 <= self.trailing_stop:
                forced.append(symbol)
        allow = self.market_filter(kospi200_prices)
        reason = "KOSPI200 MA50 >= MA200" if allow else "KOSPI200 MA50 < MA200: cash 100%"
        return RiskDecision(allow_new_positions=allow, forced_exit_symbols=forced, reason=reason)

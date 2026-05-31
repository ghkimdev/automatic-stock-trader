from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class PortfolioOrder:
    symbol: str
    side: str
    quantity: int
    target_weight: float
    estimated_price: float


class PortfolioEngine:
    """Converts target weights into executable order quantities."""

    def target_orders(
        self,
        signals: pd.DataFrame,
        current_positions: dict[str, int],
        latest_prices: dict[str, float],
        equity: float,
    ) -> list[PortfolioOrder]:
        orders: list[PortfolioOrder] = []
        targets = {row.symbol: float(row.target_weight) for row in signals.itertuples()}
        all_symbols = set(current_positions) | set(targets)
        for symbol in sorted(all_symbols):
            price = latest_prices.get(symbol)
            if price is None or price <= 0:
                continue
            target_qty = int((equity * targets.get(symbol, 0.0)) // price)
            delta = target_qty - current_positions.get(symbol, 0)
            if delta == 0:
                continue
            orders.append(
                PortfolioOrder(
                    symbol=symbol,
                    side="BUY" if delta > 0 else "SELL",
                    quantity=abs(delta),
                    target_weight=targets.get(symbol, 0.0),
                    estimated_price=price,
                )
            )
        return orders

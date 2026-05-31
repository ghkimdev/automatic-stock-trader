from dataclasses import dataclass
from datetime import date

import pandas as pd

from trading_system.app.backtest.metrics import annual_monthly_report, performance_metrics
from trading_system.app.risk.engine import RiskEngine
from trading_system.app.strategies.base import BaseStrategy


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 100_000_000.0
    fee_rate: float = 0.00015
    slippage_rate: float = 0.001
    sell_tax_rate: float = 0.0018


class BacktestEngine:
    """Monthly close-signal, next-open-fill backtester shared by research and production strategy code."""

    def __init__(self, strategy: BaseStrategy, risk_engine: RiskEngine | None = None, config: BacktestConfig | None = None) -> None:
        self.strategy = strategy
        self.risk_engine = risk_engine or RiskEngine()
        self.config = config or BacktestConfig()

    def run(self, prices: pd.DataFrame, fundamentals: pd.DataFrame, start: date, end: date, kospi200_prices: pd.DataFrame | None = None) -> dict[str, object]:
        frame = prices[(prices["date"] >= start) & (prices["date"] <= end)].copy()
        if frame.empty:
            raise ValueError("price data is empty for backtest period")
        frame["date"] = pd.to_datetime(frame["date"])
        all_dates = sorted(frame["date"].dt.date.unique())
        rebalance_dates = self._month_end_trading_dates(all_dates)
        cash = self.config.initial_cash
        positions: dict[str, int] = {}
        avg_cost: dict[str, float] = {}
        peak_price: dict[str, float] = {}
        equity_points: list[tuple[pd.Timestamp, float]] = []
        trade_count = 0
        wins = 0
        turnover_value = 0.0
        for current in all_dates:
            daily = frame[frame["date"].dt.date == current].set_index("symbol")
            latest_prices = daily["close"].to_dict()
            for symbol, qty in list(positions.items()):
                if symbol in latest_prices:
                    peak_price[symbol] = max(peak_price.get(symbol, latest_prices[symbol]), latest_prices[symbol])
            position_state = {s: (q, avg_cost.get(s, 0.0), peak_price.get(s, 0.0)) for s, q in positions.items()}
            risk = self.risk_engine.evaluate(position_state, latest_prices, kospi200_prices if kospi200_prices is not None else pd.DataFrame())
            for symbol in risk.forced_exit_symbols:
                if symbol in positions and symbol in latest_prices:
                    cash, profit = self._sell(cash, positions, avg_cost, symbol, positions[symbol], latest_prices[symbol])
                    trade_count += 1
                    wins += int(profit > 0)
                    turnover_value += latest_prices[symbol] * positions.get(symbol, 0)
            if current in rebalance_dates:
                next_open = self._next_open(frame, current)
                if not risk.allow_new_positions:
                    signals = pd.DataFrame(columns=["symbol", "target_weight"])
                else:
                    available_fundamentals = fundamentals[fundamentals["announcement_date"] <= current]
                    signals = self.strategy.generate_signals(current, prices[prices["date"] <= current], available_fundamentals)
                target_symbols = set(signals["symbol"].tolist()) if not signals.empty else set()
                equity = cash + sum(q * latest_prices.get(s, 0.0) for s, q in positions.items())
                for symbol in list(positions):
                    if symbol not in target_symbols and symbol in next_open:
                        qty = positions[symbol]
                        cash, profit = self._sell(cash, positions, avg_cost, symbol, qty, next_open[symbol])
                        trade_count += 1
                        wins += int(profit > 0)
                        turnover_value += qty * next_open[symbol]
                for row in signals.itertuples():
                    if row.symbol not in next_open:
                        continue
                    target_value = equity * float(row.target_weight)
                    price = next_open[row.symbol] * (1 + self.config.slippage_rate)
                    desired_qty = int(target_value // price)
                    delta = desired_qty - positions.get(row.symbol, 0)
                    if delta > 0:
                        cost = delta * price * (1 + self.config.fee_rate)
                        if cost <= cash:
                            old_qty = positions.get(row.symbol, 0)
                            old_cost = avg_cost.get(row.symbol, 0.0) * old_qty
                            positions[row.symbol] = old_qty + delta
                            avg_cost[row.symbol] = (old_cost + delta * price) / positions[row.symbol]
                            peak_price[row.symbol] = max(peak_price.get(row.symbol, price), price)
                            cash -= cost
                            turnover_value += delta * price
                            trade_count += 1
                    elif delta < 0:
                        cash, profit = self._sell(cash, positions, avg_cost, row.symbol, abs(delta), next_open[row.symbol])
                        trade_count += 1
                        wins += int(profit > 0)
                        turnover_value += abs(delta) * next_open[row.symbol]
            equity = cash + sum(q * latest_prices.get(s, 0.0) for s, q in positions.items())
            equity_points.append((pd.Timestamp(current), equity))
        equity_curve = pd.Series(dict(equity_points)).sort_index()
        metrics = performance_metrics(equity_curve, turnover=turnover_value / self.config.initial_cash, trades=trade_count, wins=wins)
        return {"equity_curve": equity_curve, "metrics": metrics, "report": annual_monthly_report(equity_curve)}

    def _sell(self, cash: float, positions: dict[str, int], avg_cost: dict[str, float], symbol: str, quantity: int, price: float) -> tuple[float, float]:
        qty = min(quantity, positions.get(symbol, 0))
        fill = price * (1 - self.config.slippage_rate)
        proceeds = qty * fill * (1 - self.config.fee_rate - self.config.sell_tax_rate)
        profit = (fill - avg_cost.get(symbol, fill)) * qty
        cash += proceeds
        remaining = positions.get(symbol, 0) - qty
        if remaining <= 0:
            positions.pop(symbol, None)
            avg_cost.pop(symbol, None)
        else:
            positions[symbol] = remaining
        return cash, profit

    @staticmethod
    def _month_end_trading_dates(dates: list[date]) -> set[date]:
        series = pd.Series(pd.to_datetime(dates))
        return set(series.groupby([series.dt.year, series.dt.month]).max().dt.date.tolist())

    @staticmethod
    def _next_open(frame: pd.DataFrame, current: date) -> dict[str, float]:
        future_dates = sorted(d for d in frame["date"].dt.date.unique() if d > current)
        if not future_dates:
            return {}
        daily = frame[frame["date"].dt.date == future_dates[0]].set_index("symbol")
        return daily["open"].to_dict()

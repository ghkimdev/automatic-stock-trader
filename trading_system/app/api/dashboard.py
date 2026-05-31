from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from trading_system.app.backtest.engine import BacktestEngine
from trading_system.app.backtest.walk_forward import WalkForwardEngine
from trading_system.app.database.models import Order, Position, Symbol, Trade
from trading_system.app.database.repositories import (
    FundamentalRepository,
    OrderRepository,
    PositionRepository,
    PriceRepository,
    SymbolRepository,
    TradeRepository,
)
from trading_system.app.portfolio.engine import PortfolioEngine
from trading_system.app.factors.engine import FactorWeights
from trading_system.app.strategies.multifactor import MultiFactorStrategy


@dataclass
class DashboardRuntimeState:
    """Mutable operator state for dashboard controls."""

    strategy_enabled: bool = True
    emergency_stop: bool = False
    trading_mode: str = "paper"
    stop_loss: float = -0.10
    factor_momentum_weight: float = 0.40
    factor_value_weight: float = 0.30
    factor_quality_weight: float = 0.30
    top_n: int = 20
    rebalance_schedule: str = "monthly_last_trading_day_15:40_KST"
    scheduler_enabled: bool = True


RUNTIME_STATE = DashboardRuntimeState()


def dashboard_overview(session: Session) -> dict[str, object]:
    today = date.today()
    positions = PositionRepository(session).list()
    latest_prices = _latest_prices_for_positions(session, positions, today)
    invested_value = sum(position.quantity * latest_prices.get(position.symbol, position.avg_price) for position in positions)
    cost_basis = sum(position.quantity * position.avg_price for position in positions)
    cash = 0.0
    total_assets = cash + invested_value
    pnl = invested_value - cost_basis
    return {
        "account": {
            "total_assets": total_assets,
            "cash": cash,
            "valuation_pnl": pnl,
            "return_rate": pnl / cost_basis if cost_basis else 0.0,
        },
        "portfolio": {
            "holding_count": len(positions),
            "cash_weight": cash / total_assets if total_assets else 1.0,
            "invested_weight": invested_value / total_assets if total_assets else 0.0,
        },
        "system": {
            "db_status": _db_status(session),
            "api_status": "ok",
            "broker_status": "paper" if RUNTIME_STATE.trading_mode == "paper" else "live_configured",
            "scheduler_status": "enabled" if RUNTIME_STATE.scheduler_enabled else "disabled",
            "strategy_enabled": RUNTIME_STATE.strategy_enabled,
            "emergency_stop": RUNTIME_STATE.emergency_stop,
            "trading_mode": RUNTIME_STATE.trading_mode,
            "as_of": datetime.utcnow().isoformat(),
        },
    }


def dashboard_portfolio(session: Session) -> dict[str, object]:
    today = date.today()
    positions = PositionRepository(session).list()
    latest_prices = _latest_prices_for_positions(session, positions, today)
    symbols = {symbol.symbol: symbol for symbol in session.scalars(select(Symbol)).all()}
    rows: list[dict[str, object]] = []
    total_value = 0.0
    sector_values: dict[str, float] = {}
    for position in positions:
        current_price = latest_prices.get(position.symbol, position.avg_price)
        market_value = current_price * position.quantity
        total_value += market_value
        symbol_meta = symbols.get(position.symbol)
        sector = symbol_meta.sector if symbol_meta and symbol_meta.sector else "UNKNOWN"
        sector_values[sector] = sector_values.get(sector, 0.0) + market_value
        pnl = (current_price - position.avg_price) * position.quantity
        rows.append(
            {
                "symbol": position.symbol,
                "name": symbol_meta.name if symbol_meta else position.symbol,
                "quantity": position.quantity,
                "avg_price": position.avg_price,
                "current_price": current_price,
                "return_rate": current_price / position.avg_price - 1 if position.avg_price else 0.0,
                "valuation_pnl": pnl,
                "market_value": market_value,
                "weight": 0.0,
                "sector": sector,
            }
        )
    for row in rows:
        row["weight"] = float(row["market_value"]) / total_value if total_value else 0.0
    return {
        "positions": rows,
        "value_curve": _portfolio_value_curve(session, positions, today - timedelta(days=365), today),
        "sector_weights": [
            {"sector": sector, "value": value, "weight": value / total_value if total_value else 0.0}
            for sector, value in sorted(sector_values.items())
        ],
    }


def dashboard_orders(session: Session, period: str = "7d") -> dict[str, object]:
    since = _period_start(period)
    orders = [order for order in OrderRepository(session).list() if order.created_at.date() >= since]
    return {"orders": [serialize_dashboard_order(order) for order in orders], "period": period}


def dashboard_trades(session: Session) -> dict[str, object]:
    rows = [serialize_dashboard_trade(trade) for trade in TradeRepository(session).list()]
    profits = [float(row["profit"]) for row in rows]
    wins = [profit for profit in profits if profit > 0]
    losses = [profit for profit in profits if profit < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    return {
        "trades": rows,
        "statistics": {
            "win_rate": len(wins) / len(profits) if profits else 0.0,
            "average_profit": sum(wins) / len(wins) if wins else 0.0,
            "average_loss": sum(losses) / len(losses) if losses else 0.0,
            "profit_factor": gross_profit / gross_loss if gross_loss else 0.0,
        },
    }


def dashboard_factors(session: Session, as_of: date | None = None) -> dict[str, object]:
    day = as_of or date.today()
    symbols = [symbol.symbol for symbol in SymbolRepository(session).active_universe(day)]
    prices = PriceRepository(session).dataframe(symbols, day - timedelta(days=430), day)
    fundamentals = FundamentalRepository(session).point_in_time_dataframe(symbols, day)
    weights = FactorWeights(RUNTIME_STATE.factor_momentum_weight, RUNTIME_STATE.factor_value_weight, RUNTIME_STATE.factor_quality_weight)
    scores = MultiFactorStrategy(top_n=RUNTIME_STATE.top_n, weights=weights).factor_engine.score(prices, fundamentals, day)
    top_frame = scores.head(RUNTIME_STATE.top_n).copy()
    top_frame["target_weight"] = min(0.05, 1.0 / RUNTIME_STATE.top_n) if not top_frame.empty else 0.0
    top = top_frame.to_dict(orient="records")
    return {"as_of": day.isoformat(), "factors": scores.to_dict(orient="records"), "top20": top, "rebalance_candidates": top}


def dashboard_risk(session: Session) -> dict[str, object]:
    today = date.today()
    positions = PositionRepository(session).list()
    latest_prices = _latest_prices_for_positions(session, positions, today)
    values = [position.quantity * latest_prices.get(position.symbol, position.avg_price) for position in positions]
    total_value = sum(values)
    concentration = max((value / total_value for value in values), default=0.0) if total_value else 0.0
    value_curve = pd.Series({pd.Timestamp(row["date"]): float(row["value"]) for row in _portfolio_value_curve(session, positions, today - timedelta(days=365), today)})
    current_mdd = 0.0
    volatility = 0.0
    if not value_curve.empty and len(value_curve) > 1:
        current_mdd = float((value_curve / value_curve.cummax() - 1).iloc[-1])
        volatility = float(value_curve.pct_change().std(ddof=0) * (252**0.5))
    warnings: list[str] = []
    if current_mdd <= -0.15:
        warnings.append("MDD -15% 돌파")
    for position in positions:
        current_price = latest_prices.get(position.symbol, position.avg_price)
        if position.avg_price and current_price / position.avg_price - 1 <= RUNTIME_STATE.stop_loss:
            warnings.append(f"{position.symbol} 손절 조건 발생")
    if not _is_last_trading_day(session, today):
        rebalance_required = False
    else:
        rebalance_required = bool(positions)
        if rebalance_required:
            warnings.append("리밸런싱 필요")
    return {
        "current_mdd": current_mdd,
        "concentration": concentration,
        "cash_weight": 0.0 if total_value else 1.0,
        "sector_concentration": max((row["weight"] for row in dashboard_portfolio(session)["sector_weights"]), default=0.0),
        "volatility": volatility,
        "warnings": warnings,
        "rebalance_required": rebalance_required,
        "emergency_stop": RUNTIME_STATE.emergency_stop,
    }


def dashboard_backtest(session: Session, start: date, end: date) -> dict[str, object]:
    prices = PriceRepository(session).dataframe(None, start - timedelta(days=430), end)
    if prices.empty:
        return {"metrics": {}, "equity_curve": [], "drawdown": [], "annual_returns": {}, "monthly_returns": {}}
    symbols = sorted(prices["symbol"].unique().tolist())
    fundamentals = FundamentalRepository(session).point_in_time_dataframe(symbols, end)
    result = BacktestEngine(MultiFactorStrategy(top_n=RUNTIME_STATE.top_n, weights=FactorWeights(RUNTIME_STATE.factor_momentum_weight, RUNTIME_STATE.factor_value_weight, RUNTIME_STATE.factor_quality_weight))).run(prices, fundamentals, start, end)
    equity_curve = result["equity_curve"]
    drawdown = equity_curve / equity_curve.cummax() - 1
    return {
        "metrics": result["metrics"],
        "equity_curve": [{"date": idx.date().isoformat(), "value": float(value)} for idx, value in equity_curve.items()],
        "drawdown": [{"date": idx.date().isoformat(), "value": float(value)} for idx, value in drawdown.items()],
        "annual_returns": result["report"]["annual_returns"],
        "monthly_returns": result["report"]["monthly_returns"],
    }


def dashboard_walkforward(session: Session, start_year: int, end_year: int) -> dict[str, object]:
    prices = PriceRepository(session).dataframe(None, date(start_year, 1, 1) - timedelta(days=430), date(end_year, 12, 31))
    if prices.empty:
        return {"windows": [], "average": {"CAGR": 0.0, "MDD": 0.0, "Sharpe Ratio": 0.0}}
    symbols = sorted(prices["symbol"].unique().tolist())
    fundamentals = FundamentalRepository(session).point_in_time_dataframe(symbols, date(end_year, 12, 31))
    rows = WalkForwardEngine(BacktestEngine(MultiFactorStrategy(top_n=RUNTIME_STATE.top_n, weights=FactorWeights(RUNTIME_STATE.factor_momentum_weight, RUNTIME_STATE.factor_value_weight, RUNTIME_STATE.factor_quality_weight)))).run(prices, fundamentals, start_year, end_year)
    records = rows.to_dict(orient="records") if not rows.empty else []
    return {"windows": records, "average": _numeric_average(records, ["CAGR", "MDD", "Sharpe Ratio"])}


def dashboard_rebalance(session: Session, execute: bool = False) -> dict[str, object]:
    if RUNTIME_STATE.emergency_stop:
        return {"status": "blocked", "reason": "emergency_stop", "orders": []}
    today = date.today()
    portfolio = dashboard_portfolio(session)
    current_positions = {row["symbol"]: int(row["quantity"]) for row in portfolio["positions"]}
    latest_prices = {row["symbol"]: float(row["current_price"]) for row in portfolio["positions"]}
    factor_payload = dashboard_factors(session, today)
    signals = pd.DataFrame(factor_payload["rebalance_candidates"])
    price_repo = PriceRepository(session)
    for symbol in signals["symbol"].tolist() if not signals.empty else []:
        latest = price_repo.latest_by_symbol(symbol, today)
        if latest:
            latest_prices[symbol] = latest.close
    equity = sum(float(row["market_value"]) for row in portfolio["positions"])
    orders = [asdict(order) for order in PortfolioEngine().target_orders(signals, current_positions, latest_prices, equity)]
    return {
        "status": "executed" if execute else "simulated",
        "current_portfolio": portfolio["positions"],
        "expected_portfolio": factor_payload["rebalance_candidates"],
        "orders": orders,
    }


def update_dashboard_settings(payload: dict[str, object]) -> dict[str, object]:
    for key in asdict(RUNTIME_STATE):
        if key in payload:
            setattr(RUNTIME_STATE, key, payload[key])
    total = RUNTIME_STATE.factor_momentum_weight + RUNTIME_STATE.factor_value_weight + RUNTIME_STATE.factor_quality_weight
    if total <= 0:
        RUNTIME_STATE.factor_momentum_weight = 0.40
        RUNTIME_STATE.factor_value_weight = 0.30
        RUNTIME_STATE.factor_quality_weight = 0.30
    return asdict(RUNTIME_STATE)


def strategy_control(action: str) -> dict[str, object]:
    if action == "stop":
        RUNTIME_STATE.strategy_enabled = False
    elif action == "resume":
        RUNTIME_STATE.strategy_enabled = True
        RUNTIME_STATE.emergency_stop = False
    elif action == "emergency_stop":
        RUNTIME_STATE.strategy_enabled = False
        RUNTIME_STATE.emergency_stop = True
    elif action == "paper":
        RUNTIME_STATE.trading_mode = "paper"
    elif action == "live":
        RUNTIME_STATE.trading_mode = "live"
    return asdict(RUNTIME_STATE)


def emergency_liquidation_plan(session: Session) -> dict[str, object]:
    RUNTIME_STATE.strategy_enabled = False
    RUNTIME_STATE.emergency_stop = True
    positions = PositionRepository(session).list()
    latest_prices = _latest_prices_for_positions(session, positions, date.today())
    orders = [
        {"symbol": position.symbol, "side": "SELL", "quantity": position.quantity, "estimated_price": latest_prices.get(position.symbol, position.avg_price)}
        for position in positions
        if position.quantity > 0
    ]
    return {"status": "emergency_stop_enabled", "liquidation_orders": orders}


def read_logs(log_name: str, query: str | None = None, limit: int = 200) -> dict[str, object]:
    allowed = {"system.log", "trade.log", "error.log"}
    if log_name not in allowed:
        log_name = "system.log"
    path = Path("logs") / log_name
    if not path.exists():
        return {"log": log_name, "lines": []}
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    if query:
        lines = [line for line in lines if query.lower() in line.lower()]
    return {"log": log_name, "lines": lines[-limit:]}


def serialize_dashboard_order(order: Order) -> dict[str, object]:
    return {
        "order_time": order.created_at.isoformat(),
        "symbol": order.symbol,
        "side": order.side.value,
        "order_quantity": order.quantity,
        "filled_quantity": order.filled_quantity,
        "filled_price": order.filled_price,
        "status": order.status.value,
    }


def serialize_dashboard_trade(trade: Trade) -> dict[str, object]:
    holding_days = max((trade.exit_time - trade.entry_time).days, 0)
    return {
        "entry_date": trade.entry_time.date().isoformat(),
        "exit_date": trade.exit_time.date().isoformat(),
        "holding_days": holding_days,
        "return_rate": trade.exit_price / trade.entry_price - 1 if trade.entry_price else 0.0,
        "profit": trade.profit,
        "symbol": trade.symbol,
    }


def _latest_prices_for_positions(session: Session, positions: list[Position], as_of: date) -> dict[str, float]:
    repo = PriceRepository(session)
    prices: dict[str, float] = {}
    for position in positions:
        price = repo.latest_by_symbol(position.symbol, as_of)
        prices[position.symbol] = price.close if price else position.avg_price
    return prices


def _portfolio_value_curve(session: Session, positions: list[Position], start: date, end: date) -> list[dict[str, object]]:
    symbols = [position.symbol for position in positions]
    if not symbols:
        return []
    prices = PriceRepository(session).dataframe(symbols, start, end)
    if prices.empty:
        return []
    qty = {position.symbol: position.quantity for position in positions}
    prices["value"] = prices.apply(lambda row: row["close"] * qty.get(row["symbol"], 0), axis=1)
    curve = prices.groupby("date")["value"].sum().reset_index()
    return [{"date": row.date.isoformat(), "value": float(row.value)} for row in curve.itertuples()]


def _db_status(session: Session) -> str:
    session.execute(text("select 1"))
    return "ok"


def _period_start(period: str) -> date:
    today = date.today()
    if period == "today":
        return today
    if period == "30d":
        return today - timedelta(days=30)
    return today - timedelta(days=7)


def _is_last_trading_day(session: Session, day: date) -> bool:
    next_prices = PriceRepository(session).dataframe(None, day + timedelta(days=1), day + timedelta(days=7))
    if next_prices.empty:
        return True
    return pd.to_datetime(next_prices["date"]).min().month != day.month


def _numeric_average(records: list[dict[str, object]], keys: list[str]) -> dict[str, float]:
    average: dict[str, float] = {}
    for key in keys:
        values = [float(record[key]) for record in records if key in record]
        average[key] = sum(values) / len(values) if values else 0.0
    return average

from datetime import date, timedelta
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from trading_system.app.api.dashboard import (
    dashboard_backtest,
    dashboard_factors,
    dashboard_orders,
    dashboard_overview,
    dashboard_portfolio,
    dashboard_rebalance,
    dashboard_risk,
    dashboard_trades,
    dashboard_walkforward,
    emergency_liquidation_plan,
    read_logs,
    strategy_control,
    update_dashboard_settings,
)
from trading_system.app.backtest.engine import BacktestEngine
from trading_system.app.database.models import Order, Position, Trade
from trading_system.app.database.repositories import (
    FundamentalRepository,
    OrderRepository,
    PositionRepository,
    PriceRepository,
    SymbolRepository,
    TradeRepository,
)
from trading_system.app.database.session import get_session, init_db
from trading_system.app.strategies.multifactor import MultiFactorStrategy
from trading_system.app.utils.logging import configure_logging

configure_logging()
app = FastAPI(title="Korea Multifactor Quant Trading Platform", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunResponse(BaseModel):
    status: str
    details: dict[str, object]


class DashboardSettingsRequest(BaseModel):
    strategy_enabled: bool | None = None
    emergency_stop: bool | None = None
    trading_mode: str | None = None
    stop_loss: float | None = None
    factor_momentum_weight: float | None = None
    factor_value_weight: float | None = None
    factor_quality_weight: float | None = None
    top_n: int | None = None
    rebalance_schedule: str | None = None
    scheduler_enabled: bool | None = None


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/portfolio")
def portfolio(session: Annotated[Session, Depends(get_session)]) -> dict[str, object]:
    positions = PositionRepository(session).list()
    return {"positions": [serialize_position(p) for p in positions], "position_count": len(positions)}


@app.get("/positions")
def positions(session: Annotated[Session, Depends(get_session)]) -> list[dict[str, object]]:
    return [serialize_position(p) for p in PositionRepository(session).list()]


@app.get("/orders")
def orders(session: Annotated[Session, Depends(get_session)]) -> list[dict[str, object]]:
    return [serialize_order(o) for o in OrderRepository(session).list()]


@app.get("/trades")
def trades(session: Annotated[Session, Depends(get_session)]) -> list[dict[str, object]]:
    return [serialize_trade(t) for t in TradeRepository(session).list()]


@app.get("/factors")
def factors(session: Annotated[Session, Depends(get_session)], as_of: date | None = None) -> list[dict[str, object]]:
    day = as_of or date.today()
    symbols = [s.symbol for s in SymbolRepository(session).active_universe(day)]
    prices = PriceRepository(session).dataframe(symbols, day - timedelta(days=430), day)
    fundamentals = FundamentalRepository(session).point_in_time_dataframe(symbols, day)
    return MultiFactorStrategy().factor_engine.score(prices, fundamentals, day).to_dict(orient="records")


@app.get("/backtest")
def backtest(session: Annotated[Session, Depends(get_session)], start: date, end: date) -> dict[str, object]:
    prices = PriceRepository(session).dataframe(None, start - timedelta(days=430), end)
    symbols = sorted(prices["symbol"].unique().tolist()) if not prices.empty else []
    fundamentals_df = FundamentalRepository(session).point_in_time_dataframe(symbols, end)
    result = BacktestEngine(MultiFactorStrategy()).run(prices, fundamentals_df, start, end)
    return {"metrics": result["metrics"], "report": result["report"]}


@app.post("/strategy/run")
def run_strategy(session: Annotated[Session, Depends(get_session)]) -> RunResponse:
    day = date.today()
    symbols = [s.symbol for s in SymbolRepository(session).active_universe(day)]
    prices = PriceRepository(session).dataframe(symbols, day - timedelta(days=430), day)
    fundamentals = FundamentalRepository(session).point_in_time_dataframe(symbols, day)
    signals = MultiFactorStrategy().generate_signals(day, prices, fundamentals)
    return RunResponse(status="ok", details={"signals": signals.to_dict(orient="records")})


@app.post("/rebalance")
def rebalance(session: Annotated[Session, Depends(get_session)]) -> RunResponse:
    response = run_strategy(session)
    return RunResponse(status="accepted", details=response.details)


@app.get("/dashboard/overview")
def dashboard_overview_endpoint(session: Annotated[Session, Depends(get_session)]) -> dict[str, object]:
    return dashboard_overview(session)


@app.get("/dashboard/portfolio")
def dashboard_portfolio_endpoint(session: Annotated[Session, Depends(get_session)]) -> dict[str, object]:
    return dashboard_portfolio(session)


@app.get("/dashboard/orders")
def dashboard_orders_endpoint(session: Annotated[Session, Depends(get_session)], period: str = "7d") -> dict[str, object]:
    return dashboard_orders(session, period)


@app.get("/dashboard/trades")
def dashboard_trades_endpoint(session: Annotated[Session, Depends(get_session)]) -> dict[str, object]:
    return dashboard_trades(session)


@app.get("/dashboard/factors")
def dashboard_factors_endpoint(session: Annotated[Session, Depends(get_session)], as_of: date | None = None) -> dict[str, object]:
    return dashboard_factors(session, as_of)


@app.get("/dashboard/risk")
def dashboard_risk_endpoint(session: Annotated[Session, Depends(get_session)]) -> dict[str, object]:
    return dashboard_risk(session)


@app.get("/dashboard/backtest")
def dashboard_backtest_endpoint(session: Annotated[Session, Depends(get_session)], start: date, end: date) -> dict[str, object]:
    return dashboard_backtest(session, start, end)


@app.get("/dashboard/walkforward")
def dashboard_walkforward_endpoint(session: Annotated[Session, Depends(get_session)], start_year: int = 2014, end_year: int = 2024) -> dict[str, object]:
    return dashboard_walkforward(session, start_year, end_year)


@app.get("/dashboard/rebalance")
def dashboard_rebalance_preview_endpoint(session: Annotated[Session, Depends(get_session)]) -> dict[str, object]:
    return dashboard_rebalance(session, False)


@app.post("/dashboard/rebalance")
def dashboard_rebalance_endpoint(session: Annotated[Session, Depends(get_session)], execute: bool = False) -> dict[str, object]:
    return dashboard_rebalance(session, execute)


@app.post("/dashboard/strategy/{action}")
def dashboard_strategy_control_endpoint(action: str) -> dict[str, object]:
    return strategy_control(action)


@app.post("/dashboard/emergency-stop")
def dashboard_emergency_stop_endpoint(session: Annotated[Session, Depends(get_session)]) -> dict[str, object]:
    return emergency_liquidation_plan(session)


@app.get("/dashboard/logs")
def dashboard_logs_endpoint(log_name: str = "system.log", query: str | None = None, limit: int = 200) -> dict[str, object]:
    return read_logs(log_name, query, limit)


@app.post("/dashboard/admin/settings")
def dashboard_settings_endpoint(payload: DashboardSettingsRequest) -> dict[str, object]:
    return update_dashboard_settings(payload.model_dump(exclude_none=True))


def serialize_order(order: Order) -> dict[str, object]:
    return {
        "id": order.id,
        "symbol": order.symbol,
        "side": order.side.value,
        "quantity": order.quantity,
        "filled_quantity": order.filled_quantity,
        "price": order.price,
        "filled_price": order.filled_price,
        "status": order.status.value,
        "created_at": order.created_at.isoformat(),
    }


def serialize_position(position: Position) -> dict[str, object]:
    return {"symbol": position.symbol, "quantity": position.quantity, "avg_price": position.avg_price, "peak_price": position.peak_price}


def serialize_trade(trade: Trade) -> dict[str, object]:
    return {"id": trade.id, "symbol": trade.symbol, "entry_price": trade.entry_price, "exit_price": trade.exit_price, "profit": trade.profit, "entry_time": trade.entry_time.isoformat(), "exit_time": trade.exit_time.isoformat()}

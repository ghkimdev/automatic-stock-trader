from datetime import date, timedelta
from typing import Annotated

from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy.orm import Session

from trading_system.app.backtest.engine import BacktestEngine
from trading_system.app.database.models import Order, Position, Trade
from trading_system.app.database.repositories import FundamentalRepository, OrderRepository, PositionRepository, PriceRepository, SymbolRepository, TradeRepository
from trading_system.app.database.session import get_session, init_db
from trading_system.app.strategies.multifactor import MultiFactorStrategy
from trading_system.app.utils.logging import configure_logging

configure_logging()
app = FastAPI(title="Korea Multifactor Quant Trading Platform", version="0.1.0")


class RunResponse(BaseModel):
    status: str
    details: dict[str, object]


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
    fundamentals = session.query  # keep session dependency alive for injection-friendly construction
    del fundamentals
    fundamentals_df = FundamentalRepository(session).point_in_time_dataframe(sorted(prices["symbol"].unique().tolist()) if not prices.empty else [], end)
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


def serialize_order(order: Order) -> dict[str, object]:
    return {"id": order.id, "symbol": order.symbol, "side": order.side.value, "quantity": order.quantity, "price": order.price, "status": order.status.value, "created_at": order.created_at.isoformat()}


def serialize_position(position: Position) -> dict[str, object]:
    return {"symbol": position.symbol, "quantity": position.quantity, "avg_price": position.avg_price, "peak_price": position.peak_price}


def serialize_trade(trade: Trade) -> dict[str, object]:
    return {"id": trade.id, "symbol": trade.symbol, "entry_price": trade.entry_price, "exit_price": trade.exit_price, "profit": trade.profit, "entry_time": trade.entry_time.isoformat(), "exit_time": trade.exit_time.isoformat()}

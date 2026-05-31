from datetime import date, timedelta
from typing import Any

import pandas as pd
from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from trading_system.app.database.models import Fundamental, Order, Position, Price, Symbol, Trade


class SymbolRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_many(self, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            obj = self.session.get(Symbol, row["symbol"])
            if obj is None:
                self.session.add(Symbol(**row))
            else:
                for key, value in row.items():
                    setattr(obj, key, value)
        self.session.commit()

    def active_universe(self, as_of: date) -> list[Symbol]:
        six_months_ago = as_of - timedelta(days=183)
        stmt = select(Symbol).where(
            Symbol.market.in_(["KOSPI", "KOSDAQ"]),
            Symbol.listing_date <= six_months_ago,
            (Symbol.delisting_date.is_(None)) | (Symbol.delisting_date > as_of),
            Symbol.security_type == "COMMON_STOCK",
            Symbol.is_spac.is_(False),
            Symbol.is_preferred.is_(False),
            Symbol.is_administrative.is_(False),
            Symbol.is_halted.is_(False),
        )
        return list(self.session.scalars(stmt))


class PriceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_many(self, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            obj = self.session.get(Price, {"date": row["date"], "symbol": row["symbol"]})
            if obj is None:
                self.session.add(Price(**row))
            else:
                for key, value in row.items():
                    setattr(obj, key, value)
        self.session.commit()

    def dataframe(self, symbols: list[str] | None, start: date, end: date) -> pd.DataFrame:
        stmt = select(Price).where(Price.date >= start, Price.date <= end)
        if symbols:
            stmt = stmt.where(Price.symbol.in_(symbols))
        rows = self.session.scalars(stmt).all()
        return pd.DataFrame(
            [
                {
                    "date": r.date,
                    "symbol": r.symbol,
                    "open": r.open,
                    "high": r.high,
                    "low": r.low,
                    "close": r.close,
                    "volume": r.volume,
                    "market_cap": r.market_cap,
                    "trading_value": r.trading_value or r.close * r.volume,
                }
                for r in rows
            ]
        )

    def latest_by_symbol(self, symbol: str, as_of: date) -> Price | None:
        stmt = select(Price).where(Price.symbol == symbol, Price.date <= as_of).order_by(Price.date.desc())
        return self.session.scalars(stmt).first()


class FundamentalRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_many(self, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            stmt = select(Fundamental).where(
                Fundamental.symbol == row["symbol"],
                Fundamental.announcement_date == row["announcement_date"],
            )
            obj = self.session.scalars(stmt).first()
            if obj is None:
                self.session.add(Fundamental(**row))
            else:
                for key, value in row.items():
                    setattr(obj, key, value)
        self.session.commit()

    def point_in_time_dataframe(self, symbols: list[str], as_of: date) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        for symbol in symbols:
            stmt = (
                select(Fundamental)
                .where(Fundamental.symbol == symbol, Fundamental.announcement_date <= as_of)
                .order_by(Fundamental.announcement_date.desc())
            )
            f = self.session.scalars(stmt).first()
            if f:
                rows.append({c.name: getattr(f, c.name) for c in Fundamental.__table__.columns})
        return pd.DataFrame(rows)


class OrderRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, order: Order) -> Order:
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        return order

    def list(self) -> list[Order]:
        return list(self.session.scalars(select(Order).order_by(Order.created_at.desc())))


class PositionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Position]:
        return list(self.session.scalars(select(Position)))

    def save(self, position: Position) -> Position:
        self.session.merge(position)
        self.session.commit()
        return position


class TradeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, trade: Trade) -> Trade:
        self.session.add(trade)
        self.session.commit()
        self.session.refresh(trade)
        return trade

    def list(self) -> list[Trade]:
        return list(self.session.scalars(select(Trade).order_by(Trade.exit_time.desc())))

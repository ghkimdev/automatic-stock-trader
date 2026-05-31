from datetime import date, datetime
from enum import StrEnum
from typing import Optional

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class OrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(StrEnum):
    NEW = "NEW"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"


class Symbol(Base):
    __tablename__ = "symbols"

    symbol: Mapped[str] = mapped_column(String(12), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    market: Mapped[str] = mapped_column(String(20), nullable=False)
    sector: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    listing_date: Mapped[date] = mapped_column(Date, nullable=False)
    delisting_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    security_type: Mapped[str] = mapped_column(String(30), default="COMMON_STOCK", nullable=False)
    is_spac: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_preferred: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_administrative: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_halted: Mapped[bool] = mapped_column(default=False, nullable=False)

    prices: Mapped[list["Price"]] = relationship(back_populates="symbol_ref")


class Price(Base):
    __tablename__ = "prices"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    symbol: Mapped[str] = mapped_column(ForeignKey("symbols.symbol"), primary_key=True)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)
    market_cap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    trading_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    symbol_ref: Mapped[Symbol] = relationship(back_populates="prices")


class Fundamental(Base):
    __tablename__ = "fundamentals"
    __table_args__ = (UniqueConstraint("symbol", "announcement_date", name="uq_fundamental_symbol_announcement"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(ForeignKey("symbols.symbol"), nullable=False, index=True)
    announcement_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    per: Mapped[Optional[float]] = mapped_column(Float)
    pbr: Mapped[Optional[float]] = mapped_column(Float)
    psr: Mapped[Optional[float]] = mapped_column(Float)
    pcr: Mapped[Optional[float]] = mapped_column(Float)
    ev_ebitda: Mapped[Optional[float]] = mapped_column(Float)
    roe: Mapped[Optional[float]] = mapped_column(Float)
    roa: Mapped[Optional[float]] = mapped_column(Float)
    operating_margin: Mapped[Optional[float]] = mapped_column(Float)
    debt_ratio: Mapped[Optional[float]] = mapped_column(Float)
    current_ratio: Mapped[Optional[float]] = mapped_column(Float)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    side: Mapped[OrderSide] = mapped_column(Enum(OrderSide), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Optional[float]] = mapped_column(Float)
    order_type: Mapped[str] = mapped_column(String(20), default="MARKET", nullable=False)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.NEW, nullable=False)
    broker_order_id: Mapped[Optional[str]] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Position(Base):
    __tablename__ = "positions"

    symbol: Mapped[str] = mapped_column(String(12), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_price: Mapped[float] = mapped_column(Float, nullable=False)
    peak_price: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    exit_price: Mapped[float] = mapped_column(Float, nullable=False)
    profit: Mapped[float] = mapped_column(Float, nullable=False)
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    exit_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index("ix_prices_symbol_date", Price.symbol, Price.date)
Index("ix_prices_date", Price.date)

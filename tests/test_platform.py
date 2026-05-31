from datetime import date, timedelta

import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from trading_system.app.api.main import app
from trading_system.app.backtest.engine import BacktestEngine
from trading_system.app.database.models import Base, Symbol
from trading_system.app.database.repositories import FundamentalRepository, SymbolRepository
from trading_system.app.database.session import make_engine
from trading_system.app.factors.engine import FactorEngine
from trading_system.app.strategies.multifactor import MultiFactorStrategy


def sample_prices() -> pd.DataFrame:
    rows = []
    start = pd.Timestamp("2023-01-02")
    symbols = ["005930", "000660", "035420", "051910"]
    for i, day in enumerate(pd.bdate_range(start, periods=320)):
        for j, symbol in enumerate(symbols):
            base = 10_000 + j * 2_000
            close = base * (1 + 0.0008 * i + 0.0002 * j * i)
            rows.append(
                {
                    "date": day.date(),
                    "symbol": symbol,
                    "open": close * 0.999,
                    "high": close * 1.01,
                    "low": close * 0.99,
                    "close": close,
                    "volume": 1_000_000,
                    "market_cap": close * 10_000_000,
                    "trading_value": close * 1_000_000,
                }
            )
    return pd.DataFrame(rows)


def sample_fundamentals(announcement: date = date(2023, 3, 31)) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"symbol": "005930", "announcement_date": announcement, "fiscal_year": 2022, "per": 8, "pbr": 1.0, "psr": 1.1, "pcr": 7, "ev_ebitda": 5, "roe": 0.15, "roa": 0.10, "operating_margin": 0.20, "debt_ratio": 0.4, "current_ratio": 2.0},
            {"symbol": "000660", "announcement_date": announcement, "fiscal_year": 2022, "per": 11, "pbr": 1.2, "psr": 1.5, "pcr": 9, "ev_ebitda": 6, "roe": 0.12, "roa": 0.08, "operating_margin": 0.17, "debt_ratio": 0.6, "current_ratio": 1.7},
            {"symbol": "035420", "announcement_date": announcement, "fiscal_year": 2022, "per": 18, "pbr": 2.0, "psr": 3.0, "pcr": 13, "ev_ebitda": 10, "roe": 0.09, "roa": 0.05, "operating_margin": 0.12, "debt_ratio": 0.8, "current_ratio": 1.3},
            {"symbol": "051910", "announcement_date": announcement, "fiscal_year": 2022, "per": 14, "pbr": 1.6, "psr": 2.0, "pcr": 11, "ev_ebitda": 8, "roe": 0.11, "roa": 0.07, "operating_margin": 0.15, "debt_ratio": 0.7, "current_ratio": 1.5},
        ]
    )


def test_factor_engine_scores_all_components() -> None:
    prices = sample_prices()
    fundamentals = sample_fundamentals()
    scores = FactorEngine().score(prices, fundamentals, date(2024, 3, 20))
    assert {"symbol", "momentum", "value", "quality", "score"}.issubset(scores.columns)
    assert len(scores) == 4
    assert scores["score"].is_monotonic_decreasing


def test_survivorship_bias_repository_filters_as_of_date() -> None:
    engine = make_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    SymbolRepository(session).upsert_many(
        [
            {"symbol": "AAA", "name": "Active", "market": "KOSPI", "sector": "IT", "listing_date": date(2020, 1, 1), "delisting_date": None, "security_type": "COMMON_STOCK", "is_spac": False, "is_preferred": False, "is_administrative": False, "is_halted": False},
            {"symbol": "BBB", "name": "Delisted", "market": "KOSDAQ", "sector": "IT", "listing_date": date(2020, 1, 1), "delisting_date": date(2023, 1, 1), "security_type": "COMMON_STOCK", "is_spac": False, "is_preferred": False, "is_administrative": False, "is_halted": False},
            {"symbol": "CCC", "name": "New", "market": "KOSPI", "sector": "IT", "listing_date": date(2024, 1, 1), "delisting_date": None, "security_type": "COMMON_STOCK", "is_spac": False, "is_preferred": False, "is_administrative": False, "is_halted": False},
        ]
    )
    symbols = {s.symbol for s in SymbolRepository(session).active_universe(date(2024, 3, 1))}
    assert symbols == {"AAA"}


def test_lookahead_fundamentals_use_announcement_date() -> None:
    engine = make_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Symbol(symbol="AAA", name="A", market="KOSPI", sector="IT", listing_date=date(2020, 1, 1)))
    session.commit()
    repo = FundamentalRepository(session)
    repo.upsert_many(
        [
            {"symbol": "AAA", "announcement_date": date(2025, 3, 31), "fiscal_year": 2024, "per": 5, "pbr": 1, "psr": 1, "pcr": 5, "ev_ebitda": 4, "roe": 0.2, "roa": 0.1, "operating_margin": 0.2, "debt_ratio": 0.3, "current_ratio": 2},
        ]
    )
    assert repo.point_in_time_dataframe(["AAA"], date(2025, 3, 30)).empty
    assert len(repo.point_in_time_dataframe(["AAA"], date(2025, 4, 1))) == 1


def test_backtest_runs_with_next_open_execution() -> None:
    result = BacktestEngine(MultiFactorStrategy(top_n=2)).run(
        sample_prices(), sample_fundamentals(), date(2023, 6, 1), date(2024, 3, 20)
    )
    assert result["metrics"]["Trades"] > 0
    assert result["metrics"]["CAGR"] > -1
    assert not result["equity_curve"].empty


def test_api_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

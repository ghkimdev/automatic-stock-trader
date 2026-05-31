from datetime import date
from typing import Protocol

import pandas as pd


class PriceDataSource(Protocol):
    def fetch_prices(self, symbol: str, start: date, end: date) -> pd.DataFrame: ...


class SymbolDataSource(Protocol):
    def fetch_symbols(self) -> pd.DataFrame: ...


class PyKrxPriceCollector:
    """pykrx adapter for Korean daily OHLCV data available to retail investors."""

    def fetch_prices(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        from pykrx import stock

        raw = stock.get_market_ohlcv_by_date(start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), symbol)
        frame = raw.rename(
            columns={"시가": "open", "고가": "high", "저가": "low", "종가": "close", "거래량": "volume", "거래대금": "trading_value"}
        ).reset_index(names="date")
        frame["symbol"] = symbol
        return frame[["date", "symbol", "open", "high", "low", "close", "volume", "trading_value"]]


class FinanceDataReaderSymbolCollector:
    """FinanceDataReader adapter for KRX symbol master data."""

    def fetch_symbols(self) -> pd.DataFrame:
        import FinanceDataReader as fdr

        raw = fdr.StockListing("KRX")
        frame = raw.rename(columns={"Code": "symbol", "Name": "name", "Market": "market", "Sector": "sector"})
        frame["listing_date"] = pd.Timestamp.today().date()
        frame["delisting_date"] = None
        frame["security_type"] = "COMMON_STOCK"
        frame["is_spac"] = frame["name"].str.contains("스팩|SPAC", case=False, na=False)
        frame["is_preferred"] = frame["name"].str.contains("우|우선", na=False)
        frame["is_administrative"] = False
        frame["is_halted"] = False
        return frame[
            [
                "symbol",
                "name",
                "market",
                "sector",
                "listing_date",
                "delisting_date",
                "security_type",
                "is_spac",
                "is_preferred",
                "is_administrative",
                "is_halted",
            ]
        ]


class DartFundamentalCollector:
    """DART Open API adapter; computes factors from disclosed statements supplied to retail investors."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def normalize_statement(self, symbol: str, announcement_date: date, fiscal_year: int, metrics: dict[str, float]) -> dict[str, float | str | date | int | None]:
        equity = metrics.get("equity", 0.0)
        assets = metrics.get("assets", 0.0)
        revenue = metrics.get("revenue", 0.0)
        operating_income = metrics.get("operating_income", 0.0)
        net_income = metrics.get("net_income", 0.0)
        liabilities = metrics.get("liabilities", 0.0)
        current_assets = metrics.get("current_assets", 0.0)
        current_liabilities = metrics.get("current_liabilities", 0.0)
        market_cap = metrics.get("market_cap", 0.0)
        enterprise_value = metrics.get("enterprise_value", 0.0)
        ebitda = metrics.get("ebitda", 0.0)
        operating_cash_flow = metrics.get("operating_cash_flow", 0.0)
        return {
            "symbol": symbol,
            "announcement_date": announcement_date,
            "fiscal_year": fiscal_year,
            "per": market_cap / net_income if net_income > 0 else None,
            "pbr": market_cap / equity if equity > 0 else None,
            "psr": market_cap / revenue if revenue > 0 else None,
            "pcr": market_cap / operating_cash_flow if operating_cash_flow > 0 else None,
            "ev_ebitda": enterprise_value / ebitda if ebitda > 0 else None,
            "roe": net_income / equity if equity > 0 else None,
            "roa": net_income / assets if assets > 0 else None,
            "operating_margin": operating_income / revenue if revenue > 0 else None,
            "debt_ratio": liabilities / equity if equity > 0 else None,
            "current_ratio": current_assets / current_liabilities if current_liabilities > 0 else None,
        }

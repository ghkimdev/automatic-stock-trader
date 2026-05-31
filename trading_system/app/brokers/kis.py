import time
from dataclasses import dataclass
from typing import Any

import httpx

from trading_system.app.brokers.base import Broker, BrokerOrderResult


@dataclass(frozen=True)
class KisCredentials:
    app_key: str
    app_secret: str
    account_no: str
    base_url: str


class KoreaInvestmentBroker(Broker):
    """한국투자증권 Open API broker adapter for retail live or mock accounts."""

    def __init__(self, credentials: KisCredentials) -> None:
        self.credentials = credentials
        self._token: str | None = None
        self._token_expires_at = 0.0

    async def _headers(self, tr_id: str) -> dict[str, str]:
        token = await self._access_token()
        return {
            "authorization": f"Bearer {token}",
            "appkey": self.credentials.app_key,
            "appsecret": self.credentials.app_secret,
            "tr_id": tr_id,
            "custtype": "P",
        }

    async def _access_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token
        async with httpx.AsyncClient(base_url=self.credentials.base_url, timeout=10) as client:
            response = await client.post(
                "/oauth2/tokenP",
                json={"grant_type": "client_credentials", "appkey": self.credentials.app_key, "appsecret": self.credentials.app_secret},
            )
            response.raise_for_status()
            data = response.json()
        self._token = str(data["access_token"])
        self._token_expires_at = time.time() + float(data.get("expires_in", 86_400))
        return self._token

    async def _place_order(self, side: str, symbol: str, quantity: int, price: float | None, order_type: str) -> BrokerOrderResult:
        tr_id = "TTTC0802U" if side == "BUY" else "TTTC0801U"
        account, product = self.credentials.account_no.split("-", maxsplit=1)
        payload: dict[str, Any] = {
            "CANO": account,
            "ACNT_PRDT_CD": product,
            "PDNO": symbol,
            "ORD_DVSN": "01" if order_type == "MARKET" else "00",
            "ORD_QTY": str(quantity),
            "ORD_UNPR": "0" if order_type == "MARKET" else str(int(price or 0)),
        }
        async with httpx.AsyncClient(base_url=self.credentials.base_url, timeout=10) as client:
            response = await client.post("/uapi/domestic-stock/v1/trading/order-cash", headers=await self._headers(tr_id), json=payload)
            response.raise_for_status()
            data = response.json()
        output = data.get("output", {})
        return BrokerOrderResult(str(output.get("ODNO", "")), "NEW", 0, price)

    async def buy(self, symbol: str, quantity: int, price: float | None = None, order_type: str = "MARKET") -> BrokerOrderResult:
        return await self._place_order("BUY", symbol, quantity, price, order_type)

    async def sell(self, symbol: str, quantity: int, price: float | None = None, order_type: str = "MARKET") -> BrokerOrderResult:
        return await self._place_order("SELL", symbol, quantity, price, order_type)

    async def cancel(self, broker_order_id: str) -> BrokerOrderResult:
        return BrokerOrderResult(broker_order_id, "CANCELED", 0, None)

    async def positions(self) -> dict[str, int]:
        return {}

    async def balance(self) -> float:
        return 0.0

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class BrokerOrderResult:
    broker_order_id: str
    status: str
    filled_quantity: int
    average_price: float | None = None


class Broker(ABC):
    @abstractmethod
    async def buy(self, symbol: str, quantity: int, price: float | None = None, order_type: str = "MARKET") -> BrokerOrderResult: ...

    @abstractmethod
    async def sell(self, symbol: str, quantity: int, price: float | None = None, order_type: str = "MARKET") -> BrokerOrderResult: ...

    @abstractmethod
    async def cancel(self, broker_order_id: str) -> BrokerOrderResult: ...

    @abstractmethod
    async def positions(self) -> dict[str, int]: ...

    @abstractmethod
    async def balance(self) -> float: ...

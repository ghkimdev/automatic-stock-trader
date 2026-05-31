from trading_system.app.brokers.base import Broker, BrokerOrderResult


class MockBroker(Broker):
    """Deterministic broker for integration tests and paper trading."""

    def __init__(self, cash: float = 100_000_000.0) -> None:
        self.cash = cash
        self.holdings: dict[str, int] = {}
        self.sequence = 0

    async def buy(self, symbol: str, quantity: int, price: float | None = None, order_type: str = "MARKET") -> BrokerOrderResult:
        self.sequence += 1
        fill_price = price or 1.0
        self.cash -= fill_price * quantity
        self.holdings[symbol] = self.holdings.get(symbol, 0) + quantity
        return BrokerOrderResult(f"MOCK-{self.sequence}", "FILLED", quantity, fill_price)

    async def sell(self, symbol: str, quantity: int, price: float | None = None, order_type: str = "MARKET") -> BrokerOrderResult:
        self.sequence += 1
        fill_price = price or 1.0
        self.cash += fill_price * quantity
        self.holdings[symbol] = max(0, self.holdings.get(symbol, 0) - quantity)
        return BrokerOrderResult(f"MOCK-{self.sequence}", "FILLED", quantity, fill_price)

    async def cancel(self, broker_order_id: str) -> BrokerOrderResult:
        return BrokerOrderResult(broker_order_id, "CANCELED", 0, None)

    async def positions(self) -> dict[str, int]:
        return dict(self.holdings)

    async def balance(self) -> float:
        return self.cash

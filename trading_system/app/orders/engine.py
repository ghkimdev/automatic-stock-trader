from loguru import logger
from sqlalchemy.orm import Session

from trading_system.app.brokers.base import Broker
from trading_system.app.database.models import Order, OrderSide, OrderStatus
from trading_system.app.database.repositories import OrderRepository
from trading_system.app.portfolio.engine import PortfolioOrder


class OrderEngine:
    """Asynchronously submits market/limit orders and records broker status."""

    def __init__(self, broker: Broker, session: Session) -> None:
        self.broker = broker
        self.order_repo = OrderRepository(session)

    async def submit(self, order: PortfolioOrder, order_type: str = "MARKET") -> Order:
        side = OrderSide.BUY if order.side == "BUY" else OrderSide.SELL
        if side is OrderSide.BUY:
            result = await self.broker.buy(order.symbol, order.quantity, order.estimated_price, order_type)
        else:
            result = await self.broker.sell(order.symbol, order.quantity, order.estimated_price, order_type)
        db_order = Order(
            symbol=order.symbol,
            side=side,
            quantity=order.quantity,
            price=order.estimated_price,
            filled_quantity=result.filled_quantity,
            filled_price=result.average_price,
            order_type=order_type,
            status=OrderStatus(result.status) if result.status in {status.value for status in OrderStatus} else OrderStatus.NEW,
            broker_order_id=result.broker_order_id,
        )
        saved = self.order_repo.add(db_order)
        logger.bind(trade=True).info("submitted order {} {} {}", saved.side, saved.symbol, saved.quantity)
        return saved

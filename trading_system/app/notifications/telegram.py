import httpx
from loguru import logger


class TelegramNotifier:
    """Sends operational alerts for fills, stops, rebalances, and errors."""

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id

    async def send(self, message: str) -> None:
        if not self.bot_token or not self.chat_id:
            logger.info("telegram disabled: {}", message)
            return
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json={"chat_id": self.chat_id, "text": message})
            response.raise_for_status()

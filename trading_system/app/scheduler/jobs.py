import asyncio
from collections.abc import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger


class TradingScheduler:
    """APScheduler wrapper that runs strategy/rebalance after Korean market close."""

    def __init__(self, rebalance_job: Callable[[], object], hour: int = 15, minute: int = 40) -> None:
        self.scheduler = BackgroundScheduler(timezone="Asia/Seoul")
        self.rebalance_job = rebalance_job
        self.hour = hour
        self.minute = minute

    def start(self) -> None:
        self.scheduler.add_job(self._run_rebalance, "cron", day_of_week="mon-fri", hour=self.hour, minute=self.minute, id="daily_rebalance", replace_existing=True)
        self.scheduler.start()
        logger.info("scheduler started at {:02d}:{:02d} KST", self.hour, self.minute)

    def shutdown(self) -> None:
        self.scheduler.shutdown(wait=False)

    def _run_rebalance(self) -> None:
        result = self.rebalance_job()
        if asyncio.iscoroutine(result):
            asyncio.run(result)

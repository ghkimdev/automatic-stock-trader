from pathlib import Path
from loguru import logger


def configure_logging(log_dir: str = "logs") -> None:
    """Configure Loguru sinks for system, trade, and error logs."""

    Path(log_dir).mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(Path(log_dir) / "system.log", rotation="10 MB", retention="30 days", level="INFO")
    logger.add(Path(log_dir) / "trade.log", rotation="10 MB", retention="90 days", level="INFO", filter=lambda record: record["extra"].get("trade", False))
    logger.add(Path(log_dir) / "error.log", rotation="10 MB", retention="90 days", level="ERROR")
    logger.add(lambda msg: print(msg, end=""), level="INFO")

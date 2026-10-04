# logger.py
import logging
import sys
from settings import settings


def _configure_logger() -> logging.Logger:
    logger = logging.getLogger("quiz_agent")
    if logger.handlers:
        return logger

    logger.setLevel(settings.LOG_LEVEL.upper())
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


logger = _configure_logger()
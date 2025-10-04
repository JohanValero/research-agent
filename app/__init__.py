"""
Project: research-agent.py
File: app/__init__.py
"""
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
LOGGER_NAME: str = 'aiexe-research'
logger : logging.Logger = logging.getLogger(LOGGER_NAME)

__all__ = [
    "LOGGER_NAME",
    "logger"
]

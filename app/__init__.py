"""
Project: research-agent.py
File: app/__init__.py
"""
import os
import logging

from dotenv import load_dotenv

load_dotenv(override=False)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
LOGGER_NAME: str = 'aiexe-research'
logger : logging.Logger = logging.getLogger(LOGGER_NAME)
logger.setLevel(logging.DEBUG)

__all__ = [
    "LOGGER_NAME",
    "logger"
]

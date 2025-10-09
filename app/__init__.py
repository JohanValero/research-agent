"""
Project: research-agent.py
File: app/__init__.py
"""
import logging

from dotenv import load_dotenv

load_dotenv(override=False)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
LOGGER_NAME: str = 'aiexe-research'
logger : logging.Logger = logging.getLogger(LOGGER_NAME)
logger.setLevel(logging.DEBUG)

COLLECTION_NAME_USERS : str = "USERS"
COLLECTION_NAME_CHATS : str = "CHATS"
COLLECTION_NAME_MESSAGES : str = "MESSAGES"

__all__ = [
    "LOGGER_NAME",
    "logger"
]

"""
Project: research-agent
File: app/db/mongodb.py
"""

import os
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app import logger


class MongoDB:
    """Gestor de conexión MongoDB"""
    client: Optional[AsyncIOMotorClient] = None
    database: Optional[AsyncIOMotorDatabase] = None

    @classmethod
    async def connect(cls):
        """Establece conexión con MongoDB"""
        try:
            mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
            db_name = os.getenv("MONGODB_DB_NAME", "research_agent")

            cls.client: Optional[AsyncIOMotorClient] = AsyncIOMotorClient(mongo_url)
            cls.database: Optional[AsyncIOMotorDatabase] = cls.client.get_database(db_name)

            # Verificar conexión
            await cls.client.admin.command('ping')
            logger.info("Conexión exitosa a MongoDB: %s", db_name)

        except Exception as e:
            logger.error("Error conectando a MongoDB: %s", str(e))
            raise

    @classmethod
    async def disconnect(cls):
        """Cierra conexión con MongoDB"""
        if cls.client:
            cls.client.close()
            logger.info("Conexión a MongoDB cerrada")

    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """Retorna instancia de la base de datos"""
        if cls.database is None:
            raise RuntimeError("Base de datos no inicializada")
        return cls.database


mongodb = MongoDB()

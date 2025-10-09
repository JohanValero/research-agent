"""
Project: research-agent
File: app/db/startup.py

Módulo de inicialización para crear índices y configuraciones de MongoDB
"""
from typing import Any, Dict, List, MutableMapping, Set
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import OperationFailure

from app import logger, COLLECTION_NAME_USERS, COLLECTION_NAME_CHATS, COLLECTION_NAME_MESSAGES

async def create_indexes(db: AsyncIOMotorDatabase) -> None:
    """
    Crea todos los índices necesarios para optimizar las consultas.
    Es idempotente - puede ejecutarse múltiples veces sin problemas.
    """
    try:
        logger.info("Iniciando creación de índices en MongoDB...")

        users_collection: AsyncIOMotorCollection = db.get_collection(COLLECTION_NAME_USERS)
        chats_collection: AsyncIOMotorCollection = db.get_collection(COLLECTION_NAME_CHATS)
        messages_collection: AsyncIOMotorCollection = db.get_collection(COLLECTION_NAME_MESSAGES)

        # Índice único en username para búsquedas rápidas y prevenir duplicados
        await users_collection.create_index([("username", ASCENDING)], unique=True, name="idx_username_unique")
        logger.info("Índice creado: USERS.username (único)")

        # Índice para filtrar por estado activo
        await users_collection.create_index([("activo", ASCENDING)], name="idx_activo")
        logger.info("Índice creado: USERS.activo")

        # Índice compuesto para listar chats de un usuario ordenados por fecha
        await chats_collection.create_index([("user_id", ASCENDING), ("updated_at", DESCENDING)], name="idx_user_updated")
        logger.info("Índice creado: CHATS.user_id + updated_at")

        # Índice simple para búsquedas por usuario
        await chats_collection.create_index([("user_id", ASCENDING)], name="idx_user_id")
        logger.info("Índice creado: CHATS.user_id")

        # Índice para filtrar chats activos
        await chats_collection.create_index([("activo", ASCENDING)], name="idx_chat_activo")
        logger.info("Índice creado: CHATS.activo")

        # Índice en last_message_id para reconstrucción de historial
        await chats_collection.create_index([("last_message_id", ASCENDING)], name="idx_last_message", sparse=True)
        logger.info("Índice creado: CHATS.last_message_id")

        # Índice compuesto para listar mensajes de un chat en orden cronológico
        await messages_collection.create_index([("chat_id", ASCENDING), ("created_at", ASCENDING)], name="idx_chat_created")
        logger.info("Índice creado: MESSAGES.chat_id + created_at")

        # Índice en previous_message_id para reconstrucción de cadena
        await messages_collection.create_index([("previous_message_id", ASCENDING)], name="idx_previous_message", sparse=True)
        logger.info("Índice creado: MESSAGES.previous_message_id")

        # Índice compuesto para queries específicas (ej: últimos mensajes de agente en un chat)
        await messages_collection.create_index(
            [("chat_id", ASCENDING), ("user_type", ASCENDING), ("created_at", DESCENDING)],
            name="idx_chat_type_created"
        )
        logger.info("Índice creado: MESSAGES.chat_id + user_type + created_at")
        logger.info("Todos los índices creados exitosamente")
    except OperationFailure as e:
        logger.error("Error creando índices: %s", str(e))
        raise
    except Exception as e:
        logger.error("Error inesperado en creación de índices: %s", str(e))
        raise

async def list_all_indexes(db: AsyncIOMotorDatabase) -> dict:
    """
    Lista todos los índices existentes en las colecciones.
    Útil para debugging y verificación.
    """
    try:
        collections: List[str] = [COLLECTION_NAME_USERS, COLLECTION_NAME_CHATS, COLLECTION_NAME_MESSAGES]
        indexes_info: Dict = {}

        for collection_name in collections:
            collection: AsyncIOMotorCollection = db.get_collection(collection_name)

            indexes: MutableMapping[str, Any] = await collection.index_information()
            indexes_info[collection_name] = indexes

            logger.info("Índices en %s:", collection_name)
            for index_name, index_spec in indexes.items():
                logger.info("  - %s: %s", index_name, index_spec.get('key'))

        return indexes_info
    except Exception as e:
        logger.error("Error listando índices: %s", str(e))
        raise


async def verify_indexes(db: AsyncIOMotorDatabase) -> bool:
    """
    Verifica que todos los índices esperados existan.
    Retorna True si todos están presentes, False en caso contrario.
    """
    try:
        expected_indexes: Dict[str, List[str]] = {
            COLLECTION_NAME_USERS: ["idx_username_unique", "idx_activo"],
            COLLECTION_NAME_CHATS: ["idx_user_updated", "idx_user_id", "idx_chat_activo", "idx_last_message"],
            COLLECTION_NAME_MESSAGES: ["idx_chat_created", "idx_previous_message", "idx_chat_type_created"]
        }

        all_present : bool = True

        for collection_name, expected in expected_indexes.items():
            collection : AsyncIOMotorCollection = db.get_collection(collection_name)
            existing : MutableMapping[str, Any] = await collection.index_information()
            existing_names : Set[str] = set(existing.keys())

            for index_name in expected:
                if index_name not in existing_names:
                    logger.warning("Índice faltante: %s.%s", collection_name, index_name)
                    all_present : bool = False

        if all_present:
            logger.info("Todos los índices esperados están presentes")
        else:
            logger.warning("Algunos índices están faltantes")

        return all_present
    except OperationFailure as e:
        logger.error("Error de operación de MongoDB al verificar índices: %s", str(e))
        return False
    except TypeError as e:
        logger.error("Error de tipo al verificar índices: %s", str(e))
        return False

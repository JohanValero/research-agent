"""
Project: research-agent
File: app/routers/messages.py
"""
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from bson import ObjectId

from app.db.mongodb import mongodb
from app.models.message import MessageCreate, MessageUpdate, MessageInDB
from app import logger

router = APIRouter(prefix="/messages", tags=["messages"])

COLLECTION_NAME: str = "MESSAGES"

@router.post("/", response_model=MessageInDB, status_code=status.HTTP_201_CREATED)
async def create_message(message: MessageCreate):
    """Crea un nuevo mensaje en la base de datos y actualiza el last_message_id del chat"""
    try:
        db: AsyncIOMotorDatabase = mongodb.get_database()
        collection: AsyncIOMotorCollection = db.get_collection(COLLECTION_NAME)
        chats_collection: AsyncIOMotorCollection = db.get_collection("CHATS")

        # Verificar que el chat existe
        if not ObjectId.is_valid(message.chat_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de chat_id inválido"
            )

        chat = await chats_collection.find_one({"_id": ObjectId(message.chat_id)})
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat {message.chat_id} no encontrado"
            )

        # Verificar que el mensaje anterior existe si se proporcionó
        if message.previous_message_id:
            if not ObjectId.is_valid(message.previous_message_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Formato de previous_message_id inválido"
                )
            
            previous = await collection.find_one({"_id": ObjectId(message.previous_message_id)})
            if not previous:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Mensaje anterior {message.previous_message_id} no encontrado"
                )

        # Preparar documento
        now: datetime = datetime.utcnow()
        message_dict: Dict[str, Any] = message.model_dump()
        message_dict["created_at"] = now
        message_dict["updated_at"] = now

        # Insertar en base de datos
        result = await collection.insert_one(message_dict)
        message_id = str(result.inserted_id)
        message_dict["_id"] = message_id

        # Actualizar el last_message_id del chat
        await chats_collection.update_one(
            {"_id": ObjectId(message.chat_id)},
            {"$set": {"last_message_id": message_id, "updated_at": now}}
        )

        logger.info("Mensaje creado: %s en chat %s", message_id, message.chat_id)
        return MessageInDB(**message_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creando mensaje: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear mensaje"
        ) from e


@router.get("/{message_id}", response_model=MessageInDB)
async def get_message(message_id: str):
    """Obtiene un mensaje por su ID"""
    try:
        db: AsyncIOMotorDatabase = mongodb.get_database()
        collection: AsyncIOMotorCollection = db.get_collection(COLLECTION_NAME)

        if not ObjectId.is_valid(message_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de message_id inválido"
            )

        message: Optional[Dict[str, Any]] = await collection.find_one({"_id": ObjectId(message_id)})
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mensaje {message_id} no encontrado"
            )

        message["_id"] = str(message["_id"])
        return MessageInDB(**message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error obteniendo mensaje: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener mensaje"
        ) from e


@router.get("/chat/{chat_id}/history", response_model=List[MessageInDB])
async def get_chat_history(chat_id: str):
    """Reconstruye el historial completo del chat siguiendo la cadena de mensajes desde last_message_id"""
    try:
        db: AsyncIOMotorDatabase = mongodb.get_database()
        chats_collection: AsyncIOMotorCollection = db.get_collection("CHATS")
        messages_collection: AsyncIOMotorCollection = db.get_collection(COLLECTION_NAME)

        if not ObjectId.is_valid(chat_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de chat_id inválido"
            )

        # Obtener el chat
        chat = await chats_collection.find_one({"_id": ObjectId(chat_id)})
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat {chat_id} no encontrado"
            )

        # Si no hay mensajes, retornar lista vacía
        if not chat.get("last_message_id"):
            return []

        # Reconstruir historial siguiendo la cadena hacia atrás
        messages = []
        current_message_id = chat["last_message_id"]

        while current_message_id:
            if not ObjectId.is_valid(current_message_id):
                break

            message = await messages_collection.find_one({"_id": ObjectId(current_message_id)})
            if not message:
                break

            message["_id"] = str(message["_id"])
            messages.insert(0, MessageInDB(**message))  # Insertar al inicio para orden correcto
            current_message_id = message.get("previous_message_id")

        return messages

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error obteniendo historial del chat: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener historial"
        ) from e


@router.get("/chat/{chat_id}", response_model=List[MessageInDB])
async def list_chat_messages(chat_id: str, skip: int = 0, limit: int = 100):
    """Lista todos los mensajes de un chat con paginación (orden cronológico)"""
    try:
        db: AsyncIOMotorDatabase = mongodb.get_database()
        collection: AsyncIOMotorCollection = db.get_collection(COLLECTION_NAME)

        if not ObjectId.is_valid(chat_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de chat_id inválido"
            )

        cursor = collection.find({"chat_id": chat_id}).sort("created_at", 1).skip(skip).limit(limit)
        messages = await cursor.to_list(length=limit)

        for message in messages:
            message["_id"] = str(message["_id"])

        return [MessageInDB(**message) for message in messages]

    except Exception as e:
        logger.error("Error listando mensajes del chat: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al listar mensajes"
        ) from e


@router.put("/{message_id}", response_model=MessageInDB)
async def update_message(message_id: str, message_update: MessageUpdate):
    """Actualiza un mensaje existente"""
    try:
        db: AsyncIOMotorDatabase = mongodb.get_database()
        collection: AsyncIOMotorCollection = db.get_collection(COLLECTION_NAME)

        if not ObjectId.is_valid(message_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de message_id inválido"
            )

        # Verificar que existe
        existing: Optional[Dict[str, Any]] = await collection.find_one({"_id": ObjectId(message_id)})
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mensaje {message_id} no encontrado"
            )

        # Actualizar solo campos proporcionados
        update_data = {k: v for k, v in message_update.model_dump().items() if v is not None}
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hay datos para actualizar"
            )

        # Convertir fragments a dict si es necesario
        if "fragments" in update_data:
            update_data["fragments"] = [f.model_dump() for f in message_update.fragments] if message_update.fragments else []

        update_data["updated_at"] = datetime.utcnow()

        await collection.update_one(
            {"_id": ObjectId(message_id)},
            {"$set": update_data}
        )

        # Obtener mensaje actualizado
        updated_message: Dict[str, Any] = await collection.find_one({"_id": ObjectId(message_id)}) # pyright: ignore[reportAssignmentType]
        updated_message["_id"] = str(updated_message["_id"])

        logger.info("Mensaje actualizado: %s", message_id)
        return MessageInDB(**updated_message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error actualizando mensaje: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar mensaje"
        ) from e


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(message_id: str):
    """Elimina un mensaje de la base de datos"""
    try:
        db = mongodb.get_database()
        collection: AsyncIOMotorCollection = db.get_collection(COLLECTION_NAME)

        if not ObjectId.is_valid(message_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de message_id inválido"
            )

        result = await collection.delete_one({"_id": ObjectId(message_id)})
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mensaje {message_id} no encontrado"
            )

        logger.info("Mensaje eliminado: %s", message_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error eliminando mensaje: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar mensaje"
        ) from e

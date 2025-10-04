"""
Project: research-agent
File: app/routers/chats.py
"""
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from bson import ObjectId

from app.db.mongodb import mongodb
from app.models.chat import ChatCreate, ChatUpdate, ChatInDB
from app import logger

router = APIRouter(prefix="/chats", tags=["chats"])

COLLECTION_NAME: str = "CHATS"

@router.post("/", response_model=ChatInDB, status_code=status.HTTP_201_CREATED)
async def create_chat(chat: ChatCreate):
    """Crea un nuevo chat en la base de datos"""
    try:
        db: AsyncIOMotorDatabase = mongodb.get_database()
        collection: AsyncIOMotorCollection = db.get_collection(COLLECTION_NAME)
        users_collection: AsyncIOMotorCollection = db.get_collection("USERS")

        # Verificar formato de user_id
        if not ObjectId.is_valid(chat.user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de user_id inválido"
            )

        # Verificar que el usuario existe
        user = await users_collection.find_one({"_id": ObjectId(chat.user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con id {chat.user_id} no encontrado"
            )

        # Preparar documento
        now: datetime = datetime.utcnow()
        chat_dict: Dict[str, Any] = chat.model_dump()
        chat_dict["created_at"] = now
        chat_dict["updated_at"] = now
        chat_dict["last_message_id"] = None

        # Insertar en base de datos
        result = await collection.insert_one(chat_dict)
        chat_dict["_id"] = str(result.inserted_id)

        logger.info("Chat creado: %s para usuario %s", chat_dict["_id"], chat.user_id)
        return ChatInDB(**chat_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creando chat: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear chat"
        ) from e


@router.get("/{chat_id}", response_model=ChatInDB)
async def get_chat(chat_id: str):
    """Obtiene un chat por su ID"""
    try:
        db: AsyncIOMotorDatabase = mongodb.get_database()
        collection: AsyncIOMotorCollection = db.get_collection(COLLECTION_NAME)

        # Validar formato de ObjectId
        if not ObjectId.is_valid(chat_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de chat_id inválido"
            )

        chat: Optional[Dict[str, Any]] = await collection.find_one({"_id": ObjectId(chat_id)})
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat {chat_id} no encontrado"
            )

        chat["_id"] = str(chat["_id"])
        return ChatInDB(**chat)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error obteniendo chat: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener chat"
        ) from e


@router.get("/user/{user_id}", response_model=List[ChatInDB])
async def list_user_chats(user_id: str, skip: int = 0, limit: int = 100):
    """Lista todos los chats de un usuario con paginación"""
    try:
        db: AsyncIOMotorDatabase = mongodb.get_database()
        collection: AsyncIOMotorCollection = db.get_collection(COLLECTION_NAME)

        # Validar formato de user_id
        if not ObjectId.is_valid(user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de user_id inválido"
            )

        cursor = collection.find({"user_id": user_id}).sort("updated_at", -1).skip(skip).limit(limit)
        chats = await cursor.to_list(length=limit)

        for chat in chats:
            chat["_id"] = str(chat["_id"])

        return [ChatInDB(**chat) for chat in chats]

    except Exception as e:
        logger.error("Error listando chats del usuario: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al listar chats"
        ) from e


@router.put("/{chat_id}", response_model=ChatInDB)
async def update_chat(chat_id: str, chat_update: ChatUpdate):
    """Actualiza un chat existente"""
    try:
        db: AsyncIOMotorDatabase = mongodb.get_database()
        collection: AsyncIOMotorCollection = db.get_collection(COLLECTION_NAME)

        if not ObjectId.is_valid(chat_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de chat_id inválido"
            )

        # Verificar que existe
        existing: Optional[Dict[str, Any]] = await collection.find_one({"_id": ObjectId(chat_id)})
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat {chat_id} no encontrado"
            )

        # Actualizar solo campos proporcionados
        update_data = {k: v for k, v in chat_update.model_dump().items() if v is not None}
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hay datos para actualizar"
            )

        update_data["updated_at"] = datetime.utcnow()

        await collection.update_one(
            {"_id": ObjectId(chat_id)},
            {"$set": update_data}
        )

        # Obtener chat actualizado
        updated_chat: Dict[str, Any] = await collection.find_one({"_id": ObjectId(chat_id)}) # pyright: ignore[reportAssignmentType]
        updated_chat["_id"] = str(updated_chat["_id"])

        logger.info("Chat actualizado: %s", chat_id)
        return ChatInDB(**updated_chat)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error actualizando chat: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar chat"
        ) from e


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(chat_id: str):
    """Elimina un chat de la base de datos"""
    try:
        db = mongodb.get_database()
        collection: AsyncIOMotorCollection = db.get_collection(COLLECTION_NAME)

        if not ObjectId.is_valid(chat_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de chat_id inválido"
            )

        result = await collection.delete_one({"_id": ObjectId(chat_id)})
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat {chat_id} no encontrado"
            )

        logger.info("Chat eliminado: %s", chat_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error eliminando chat: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar chat"
        ) from e

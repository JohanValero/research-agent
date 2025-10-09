"""
Project: research-agent
File: app/routers/users.py
"""
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection

from app.db.mongodb import mongodb
from app.models.user import UserCreate, UserUpdate, UserInDB
from app import logger, COLLECTION_NAME_USERS

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserInDB, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    """Crea un nuevo usuario en la base de datos"""
    try:
        db: AsyncIOMotorDatabase = mongodb.get_database()
        collection : AsyncIOMotorCollection = db.get_collection(COLLECTION_NAME_USERS)

        # Verificar si el usuario ya existe
        existing : Optional[Dict[str, Any]]  = await collection.find_one({"username": user.username})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Usuario con username {user.username} ya existe"
            )

        # Preparar documento
        now : datetime = datetime.utcnow()
        user_dict : Dict[str, Any] = user.model_dump()
        user_dict["created_at"] = now
        user_dict["updated_at"] = now

        # Insertar en base de datos
        result = await collection.insert_one(user_dict)
        user_dict["_id"] = str(result.inserted_id)

        logger.info("Usuario creado: %s", user.username)
        return UserInDB(**user_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creando usuario: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear usuario"
        ) from e


@router.get("/{username}", response_model=UserInDB)
async def get_user(username: str):
    """Obtiene un usuario por su username"""
    try:
        logger.debug("get_user: %s", username)
        db : AsyncIOMotorDatabase = mongodb.get_database()
        collection : AsyncIOMotorCollection = db.get_collection(COLLECTION_NAME_USERS)

        user: Optional[Dict[str, Any]] = await collection.find_one({"username": username})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario {username} no encontrado"
            )

        user["_id"] = str(user["_id"])
        return UserInDB(**user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error obteniendo usuario: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener usuario"
        ) from e


@router.get("/", response_model=List[UserInDB])
async def list_users(skip: int = 0, limit: int = 100):
    """Lista todos los usuarios con paginación"""
    try:
        db : AsyncIOMotorDatabase = mongodb.get_database()
        collection : AsyncIOMotorCollection = db.get_collection(COLLECTION_NAME_USERS)

        cursor = collection.find().skip(skip).limit(limit)
        users = await cursor.to_list(length=limit)

        for user in users:
            user["_id"] = str(user["_id"])

        return [UserInDB(**user) for user in users]

    except Exception as e:
        logger.error("Error listando usuarios: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al listar usuarios"
        ) from e


@router.put("/{username}", response_model=UserInDB)
async def update_user(username: str, user_update: UserUpdate):
    """Actualiza un usuario existente"""
    try:
        db : AsyncIOMotorDatabase = mongodb.get_database()
        collection : AsyncIOMotorCollection = db.get_collection(COLLECTION_NAME_USERS)

        # Verificar que existe
        existing : Optional[Dict[str, Any]]  = await collection.find_one({"username": username})
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario {username} no encontrado"
            )

        # Si se está actualizando el username, verificar que no exista otro con ese username
        if user_update.username and user_update.username != username:
            username_exists = await collection.find_one({"username": user_update.username})
            if username_exists:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Username {user_update.username} ya está en uso"
                )

        # Actualizar solo campos proporcionados
        update_data = {k: v for k, v in user_update.model_dump().items() if v is not None}
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hay datos para actualizar"
            )

        update_data["updated_at"] = datetime.utcnow()

        await collection.update_one(
            {"username": username},
            {"$set": update_data}
        )

        # Obtener usuario actualizado - usar el nuevo username si fue actualizado
        lookup_username = user_update.username if user_update.username else username
        updated_user : Dict[str, Any] = await collection.find_one({"username": lookup_username}) # pyright: ignore[reportAssignmentType]

        updated_user["_id"] = str(updated_user["_id"])

        logger.info("Usuario actualizado: %s", username)
        return UserInDB(**updated_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error actualizando usuario: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar usuario"
        ) from e


@router.delete("/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(username: str):
    """Elimina un usuario de la base de datos"""
    try:
        db = mongodb.get_database()
        collection : AsyncIOMotorCollection = db.get_collection(COLLECTION_NAME_USERS)

        result = await collection.delete_one({"username": username})
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario {username} no encontrado"
            )

        logger.info("Usuario eliminado: %s", username)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error eliminando usuario: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar usuario"
        ) from e

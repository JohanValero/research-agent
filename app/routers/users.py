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
from app import logger

router = APIRouter(prefix="/users", tags=["users"])

COLLECTION_NAME : str = "USERS"

@router.post("/", response_model=UserInDB, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    """Crea un nuevo usuario en la base de datos"""
    try:
        db: AsyncIOMotorDatabase = mongodb.get_database()
        collection : AsyncIOMotorCollection = db.get_collection(COLLECTION_NAME)

        # Verificar si el usuario ya existe
        existing : Optional[Dict[str, Any]]  = await collection.find_one({"numero": user.numero})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Usuario con número {user.numero} ya existe"
            )

        # Preparar documento
        now : datetime = datetime.utcnow()
        user_dict : Dict[str, Any] = user.model_dump()
        user_dict["created_at"] = now
        user_dict["updated_at"] = now

        # Insertar en base de datos
        result = await collection.insert_one(user_dict)
        user_dict["_id"] = str(result.inserted_id)

        logger.info("Usuario creado: %s", user.numero)
        return UserInDB(**user_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creando usuario: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear usuario"
        ) from e


@router.get("/{numero}", response_model=UserInDB)
async def get_user(numero: str):
    """Obtiene un usuario por su número"""
    try:
        logger.debug("get_user: %s", numero)
        db : AsyncIOMotorDatabase = mongodb.get_database()
        collection : AsyncIOMotorCollection = db.get_collection(COLLECTION_NAME)

        user: Optional[Dict[str, Any]] = await collection.find_one({"numero": numero})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario {numero} no encontrado"
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
        collection : AsyncIOMotorCollection = db.get_collection(COLLECTION_NAME)

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


@router.put("/{numero}", response_model=UserInDB)
async def update_user(numero: str, user_update: UserUpdate):
    """Actualiza un usuario existente"""
    try:
        db : AsyncIOMotorDatabase = mongodb.get_database()
        collection : AsyncIOMotorCollection = db.get_collection(COLLECTION_NAME)

        # Verificar que existe
        existing : Optional[Dict[str, Any]]  = await collection.find_one({"numero": numero})
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario {numero} no encontrado"
            )

        # Actualizar solo campos proporcionados
        update_data = {k: v for k,
                       v in user_update.model_dump().items() if v is not None}
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hay datos para actualizar"
            )

        update_data["updated_at"] = datetime.utcnow()

        await collection.update_one(
            {"numero": numero},
            {"$set": update_data}
        )

        # Obtener usuario actualizado
        updated_user : Dict[str, Any] = await collection.find_one({"numero": numero}) # pyright: ignore[reportAssignmentType]

        updated_user["_id"] = str(updated_user["_id"])

        logger.info("Usuario actualizado: %s", numero)
        return UserInDB(**updated_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error actualizando usuario: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar usuario"
        ) from e


@router.delete("/{numero}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(numero: str):
    """Elimina un usuario de la base de datos"""
    try:
        db = mongodb.get_database()
        collection : AsyncIOMotorCollection = db.get_collection(COLLECTION_NAME)

        result = await collection.delete_one({"numero": numero})
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario {numero} no encontrado"
            )

        logger.info("Usuario eliminado: %s", numero)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error eliminando usuario: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar usuario"
        ) from e

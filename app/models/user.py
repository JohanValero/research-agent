"""
Project: research-agent
File: app/models/user.py
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class UserBase(BaseModel):
    """Esquema base de usuario"""
    numero: str = Field(..., description="Número de usuario")
    nombre: Optional[str] = Field(None, description="Nombre del usuario")
    activo: bool = Field(default=True, description="Estado del usuario")

class UserCreate(UserBase):
    """Esquema para crear usuario"""

class UserUpdate(BaseModel):
    """Esquema para actualizar usuario"""
    numero: Optional[str] = None
    nombre: Optional[str] = None
    activo: Optional[bool] = None

class UserInDB(UserBase):
    """Esquema de usuario en base de datos"""
    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

    class Config:
        """Configuración"""
        populate_by_name = True

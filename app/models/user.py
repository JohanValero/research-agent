"""
Project: research-agent
File: app/models/user.py
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class UserBase(BaseModel):
    """Esquema base de usuario"""
    username: str = Field(..., description="Nombre de usuario único")
    name: str = Field(..., description="Nombre completo del usuario")
    activo: bool = Field(default=True, description="Estado del usuario")

class UserCreate(UserBase):
    """Esquema para crear usuario"""

class UserUpdate(BaseModel):
    """Esquema para actualizar usuario"""
    username: Optional[str] = None
    name: Optional[str] = None
    activo: Optional[bool] = None

class UserInDB(UserBase):
    """Esquema de usuario en base de datos"""
    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

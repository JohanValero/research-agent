"""
Project: research-agent
File: app/models/chat.py
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class ChatBase(BaseModel):
    """Esquema base de chat"""
    user_id: str = Field(..., description="ObjectId del usuario propietario del chat")
    title: Optional[str] = Field(None, description="Título del chat")
    last_message_id: Optional[str] = Field(None, description="ObjectId del último mensaje en el chat")
    activo: bool = Field(default=True, description="Estado del chat")

class ChatCreate(BaseModel):
    """Esquema para crear chat"""
    user_id: str = Field(..., description="ObjectId del usuario propietario del chat")
    title: Optional[str] = Field(None, description="Título del chat")
    activo: bool = Field(default=True, description="Estado del chat")

class ChatUpdate(BaseModel):
    """Esquema para actualizar chat"""
    title: Optional[str] = None
    last_message_id: Optional[str] = None
    activo: Optional[bool] = None

class ChatInDB(ChatBase):
    """Esquema de chat en base de datos"""
    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

"""
Project: research-agent
File: app/models/message.py
"""
from typing import Optional, List, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class MessageFragment(BaseModel):
    """Fragmento de un mensaje con diferentes tipos"""
    type: Literal["text", "table", "thought"] = Field(..., description="Tipo de fragmento")
    content: Any = Field(..., description="Contenido del fragmento")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"type": "text", "content": "Hola, ¿en qué puedo ayudarte?"},
                {"type": "thought", "content": "Necesito consultar la base de datos"},
                {"type": "table", "content": {"headers": ["Nombre", "Email"], "rows": [["Juan", "juan@example.com"]]}}
            ]
        }
    )

class MessageBase(BaseModel):
    """Esquema base de mensaje"""
    chat_id: str = Field(..., description="ID del chat al que pertenece")
    previous_message_id: Optional[str] = Field(None, description="ID del mensaje anterior en la conversación")
    user_type: Literal["HUMAN", "AGENT"] = Field(..., description="Tipo de usuario que generó el mensaje")
    fragments: List[MessageFragment] = Field(..., description="Fragmentos del mensaje")

class MessageCreate(MessageBase):
    """Esquema para crear mensaje"""

class MessageUpdate(BaseModel):
    """Esquema para actualizar mensaje"""
    fragments: Optional[List[MessageFragment]] = None

class MessageInDB(MessageBase):
    """Esquema de mensaje en base de datos"""
    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

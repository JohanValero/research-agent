"""
Project: research-agent
File: app/models/item.py
"""
from typing import Optional
from pydantic import BaseModel

class Item(BaseModel):
    """Item fast api example"""
    name: str
    description: Optional[str] = None

class ConsultaRequest(BaseModel):
    """Query basico del chat"""
    query: str
    userid: str
    chatid: Optional[str]

"""
Project: research-agent
File: app/routers/items.py
"""
from fastapi import APIRouter
from app.models.item import Item

router = APIRouter(prefix="/items", tags=["items"])

@router.get("/")
def get_items():
    """get_items: fastapi dummy example"""
    return {"message": "Lista de items"}

@router.post("/")
def create_item(item: Item):
    """create_item: fastapi dummy example"""
    return {"message": f"Item creado: {item.name}"}

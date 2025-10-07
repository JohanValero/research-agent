"""
Project: research-agent
File: app/main.py
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import logger
from app.routers import agent, items, users, chats, messages, chat_stream
from app.db.mongodb import mongodb
from app.db.startup import create_indexes, verify_indexes

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Maneja el ciclo de vida de la aplicación"""
    # Startup
    logger.info("Inicializando app: %s", _app.title)
    try:
        await mongodb.connect()
        db = mongodb.get_database()
        await create_indexes(db)
        await verify_indexes(db)
    except (ConnectionError, RuntimeError, ValueError) as e:
        logger.error("Error en inicialización de índices: %s", str(e))

    yield

    # Shutdown
    await mongodb.disconnect()

app = FastAPI(title="Research Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(items.router)
app.include_router(agent.router)
app.include_router(users.router)
app.include_router(chats.router)
app.include_router(messages.router)
app.include_router(chat_stream.router)

@app.get("/")
def read_root():
    """Root endpoint"""
    return {"message": "Research Agent API - Sistema de chats y mensajes"}

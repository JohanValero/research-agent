"""
Project: research-agent
File: app/main.py
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import logger
from app.routers import agent, items, users
from app.db.mongodb import mongodb

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Maneja el ciclo de vida de la aplicación"""
    # Startup
    logger.info("Inicializando app: %s", _app.title)
    await mongodb.connect()

    yield

    # Shutdown
    await mongodb.disconnect()

app = FastAPI(title="API Simple", lifespan=lifespan)

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

@app.get("/")
def read_root():
    """Root endpoint"""
    return {"message": "Hola Mundo desde FastAPI"}

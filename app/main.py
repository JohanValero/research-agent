"""
Project: research-agent
File: app/main.py
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import agent, items

app = FastAPI(title="API Simple")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(items.router)
app.include_router(agent.router)

@app.get("/")
def read_root():
    """Root endpoint"""
    return {"message": "Hola Mundo desde FastAPI"}

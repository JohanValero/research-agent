"""
Project: research-agent
File: app/routers/chat_stream.py
"""
from typing import AsyncGenerator, Optional
import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from bson import ObjectId

from app.db.mongodb import mongodb
from app.models.message import MessageCreate
from app.graph.graph import create_research_graph
from app import logger

router = APIRouter(prefix="/chat-stream", tags=["chat-stream"])

research_graph = create_research_graph()


async def process_user_message_and_respond(
    chat_id: str,
    user_message: str,
    previous_message_id: Optional[str] = None
) -> AsyncGenerator:
    """
    1. Guarda el mensaje del usuario
    2. Ejecuta el agente en streaming
    3. Va acumulando fragmentos de la respuesta
    4. Guarda el mensaje del agente al finalizar
    """
    try:
        db: AsyncIOMotorDatabase = mongodb.get_database()
        messages_collection: AsyncIOMotorCollection = db.get_collection("MESSAGES")
        chats_collection: AsyncIOMotorCollection = db.get_collection("CHATS")

        # Validar chat_id
        if not ObjectId.is_valid(chat_id):
            yield f"data: {json.dumps({'type': 'error', 'content': 'Formato de chat_id inválido'})}\n\n"
            return

        # Verificar que el chat existe
        chat = await chats_collection.find_one({"_id": ObjectId(chat_id)})
        if not chat:
            yield f"data: {json.dumps({'type': 'error', 'content': 'Chat no encontrado'})}\n\n"
            return

        # 1. GUARDAR MENSAJE DEL USUARIO
        now = datetime.utcnow()
        user_msg_dict = {
            "chat_id": chat_id,
            "previous_message_id": previous_message_id,
            "user_type": "HUMAN",
            "fragments": [{"type": "text", "content": user_message}],
            "created_at": now,
            "updated_at": now
        }

        result = await messages_collection.insert_one(user_msg_dict)
        user_message_id = str(result.inserted_id)

        # Actualizar last_message_id del chat
        await chats_collection.update_one(
            {"_id": ObjectId(chat_id)},
            {"$set": {"last_message_id": user_message_id, "updated_at": now}}
        )

        logger.info("Mensaje de usuario guardado: %s", user_message_id)

        # Notificar que el mensaje del usuario fue guardado
        yield f"data: {json.dumps({'type': 'user_message_saved', 'message_id': user_message_id})}\n\n"

        # 2. EJECUTAR AGENTE Y RECOLECTAR FRAGMENTOS
        agent_fragments = []

        initial_state = {
            "query": user_message,
            "userid": chat.get("user_id", "unknown"),
            "chatid": chat_id,
            "messages": [],
            "current_step": "starting"
        }

        # Notificar inicio del agente
        yield f"data: {json.dumps({'type': 'agent_start', 'content': 'Procesando tu consulta...'})}\n\n"

        # Stream de eventos del agente
        async for event in research_graph.astream_events(initial_state, version="v2"):
            event_type = event.get("event")

            if event_type == "on_chain_stream":
                chunk = event.get("data", {}).get("chunk", {})
                node_name = event.get("name", "unknown")
                messages = chunk.get("messages", [])
                current_step = chunk.get("current_step", "")

                for message in messages:
                    # Preparar datos para streaming
                    stream_data = {
                        "node": node_name,
                        "type": message.get("type", "info"),
                        "content": message.get("content", ""),
                        "details": message.get("details", {}),
                        "step": current_step
                    }

                    # Enviar al cliente
                    yield f"data: {json.dumps(stream_data, ensure_ascii=False)}\n\n"

                    # Guardar fragmentos para el mensaje final
                    # Distinguir entre pensamientos (thoughts) y texto normal
                    fragment_type = "thought" if message.get("type") in ["analysis", "research"] else "text"
                    agent_fragments.append({
                        "type": fragment_type,
                        "content": message.get("content", "")
                    })

        # 3. GUARDAR MENSAJE DEL AGENTE CON TODOS LOS FRAGMENTOS
        now = datetime.utcnow()
        agent_msg_dict = {
            "chat_id": chat_id,
            "previous_message_id": user_message_id,  # El anterior es el mensaje del usuario
            "user_type": "AGENT",
            "fragments": agent_fragments,
            "created_at": now,
            "updated_at": now
        }

        result = await messages_collection.insert_one(agent_msg_dict)
        agent_message_id = str(result.inserted_id)

        # Actualizar last_message_id del chat al mensaje del agente
        await chats_collection.update_one(
            {"_id": ObjectId(chat_id)},
            {"$set": {"last_message_id": agent_message_id, "updated_at": now}}
        )

        logger.info("Mensaje del agente guardado: %s con %d fragmentos", 
                   agent_message_id, len(agent_fragments))

        # Notificar finalización
        yield f"data: {json.dumps({'type': 'done', 'message_id': agent_message_id, 'status': 'success'})}\n\n"

    except (ValueError, TypeError, RuntimeError) as e:
        logger.error("Error en proceso de chat streaming: %s", str(e))
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"


@router.post("/send")
async def send_message_with_agent_response(message: MessageCreate) -> StreamingResponse:
    """
    Endpoint que:
    1. Guarda el mensaje del usuario
    2. Activa el agente en streaming
    3. Guarda la respuesta del agente
    """
    if message.user_type != "HUMAN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este endpoint solo acepta mensajes de usuario (HUMAN)"
        )

    if not message.fragments or len(message.fragments) != 1 or message.fragments[0].type != "text":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El mensaje debe contener exactamente un fragmento de tipo 'text'"
        )

    user_message = message.fragments[0].content
    logger.info("Nueva consulta en chat %s: %s", message.chat_id, user_message)

    return StreamingResponse(
        process_user_message_and_respond(
            message.chat_id,
            user_message,
            message.previous_message_id
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "X-Accel-Buffering": "no"
        }
    )

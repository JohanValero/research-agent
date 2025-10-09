"""
Project: research-agent
File: app/routers/chat_stream.py

Router actualizado para manejar streaming del LLM de forma eficiente.
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
    Procesa el mensaje del usuario y genera una respuesta con el agente LLM.

    Este flujo maneja:
    1. Guardar el mensaje del usuario en la base de datos
    2. Cargar el historial previo del chat para contexto
    3. Ejecutar el agente con streaming en tiempo real
    4. Acumular los fragmentos de la respuesta del LLM
    5. Guardar la respuesta completa del agente

    El streaming funciona emitiendo eventos SSE (Server-Sent Events) que el cliente
    puede procesar en tiempo real para mostrar la respuesta progresivamente.
    """
    try:
        db: AsyncIOMotorDatabase = mongodb.get_database()
        messages_collection: AsyncIOMotorCollection = db.get_collection("MESSAGES")
        chats_collection: AsyncIOMotorCollection = db.get_collection("CHATS")

        # ===== VALIDACIÓN DEL CHAT =====
        if not ObjectId.is_valid(chat_id):
            yield f"data: {json.dumps({'type': 'error', 'content': 'Formato de chat_id inválido'})}\n\n"
            return

        chat = await chats_collection.find_one({"_id": ObjectId(chat_id)})
        if not chat:
            yield f"data: {json.dumps({'type': 'error', 'content': 'Chat no encontrado'})}\n\n"
            return

        # ===== GUARDAR MENSAJE DEL USUARIO =====
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

        # Actualizar el chat con el último mensaje
        await chats_collection.update_one(
            {"_id": ObjectId(chat_id)},
            {"$set": {"last_message_id": user_message_id, "updated_at": now}}
        )

        logger.info("Mensaje del usuario guardado: %s en chat %s",
                    user_message_id, chat_id)

        # Notificar al cliente que el mensaje fue guardado
        yield f"data: {json.dumps({'type': 'user_message_saved', 'message_id': user_message_id})}\n\n"

        # ===== CARGAR HISTORIAL PARA CONTEXTO =====
        # Reconstruir los últimos N mensajes del chat para dar contexto al LLM
        # Esto permite que el LLM entienda la conversación previa
        conversation_history = []
        try:
            # Obtener los últimos 10 mensajes del chat para contexto
            # En producción, podrías ajustar este número basándote en el límite de tokens del modelo
            cursor = messages_collection.find({"chat_id": chat_id}).sort("created_at", -1).limit(10)

            history_messages = await cursor.to_list(length=10)
            history_messages.reverse()  # Ordenar cronológicamente

            # Convertir a formato OpenAI para el LLM
            for msg in history_messages:
                role = "user" if msg["user_type"] == "HUMAN" else "assistant"
                # Combinar todos los fragmentos de texto en un solo contenido
                content_parts = []
                for fragment in msg.get("fragments", []):
                    if fragment["type"] == "text":
                        content_parts.append(fragment["content"])

                if content_parts:
                    conversation_history.append({
                        "role": role,
                        "content": " ".join(content_parts)
                    })

            logger.info("Historial cargado: %d mensajes previos",
                        len(conversation_history))

        except Exception as e:
            logger.warning(
                "Error cargando historial: %s. Continuando sin contexto.", str(e))
            conversation_history = []

        # ===== EJECUTAR AGENTE CON STREAMING =====
        # Estas variables acumulan los diferentes tipos de contenido
        agent_fragments = []  # Todos los fragmentos para guardar
        response_text_chunks = []  # Solo los chunks de texto de la respuesta final

        initial_state = {
            "query": user_message,
            "userid": chat.get("user_id", "unknown"),
            "chatid": chat_id,
            "messages": [],
            "current_step": "starting",
            "conversation_history": conversation_history  # Pasar el contexto al grafo
        }

        # Notificar inicio del procesamiento
        yield f"data: {json.dumps({'type': 'agent_start', 'content': 'Procesando tu consulta...'})}\n\n"

        # Procesar eventos del grafo
        async for event in research_graph.astream_events(initial_state, version="v2"):
            event_type = event.get("event")

            if event_type == "on_chain_stream":
                chunk = event.get("data", {}).get("chunk", {})
                node_name = event.get("name", "unknown")
                messages = chunk.get("messages", [])
                current_step = chunk.get("current_step", "")

                for message in messages:
                    message_type = message.get("type", "info")
                    content = message.get("content", "")
                    details = message.get("details", {})

                    # Preparar datos para el cliente
                    stream_data = {
                        "node": node_name,
                        "type": message_type,
                        "content": content,
                        "details": details,
                        "step": current_step
                    }

                    # Enviar al cliente en tiempo real
                    yield f"data: {json.dumps(stream_data, ensure_ascii=False)}\n\n"

                    # ===== ACUMULAR FRAGMENTOS PARA GUARDAR =====
                    # Distinguir entre diferentes tipos de contenido:
                    # - analysis/research = pensamientos internos (thoughts)
                    # - response = respuesta real al usuario (text)
                    # - finalize = metadata de finalización (no se guarda)

                    if message_type in ["analysis", "research"]:
                        # Pensamientos del agente durante el procesamiento
                        if content.strip():  # Solo guardar si hay contenido
                            agent_fragments.append({
                                "type": "thought",
                                "content": content
                            })

                    elif message_type == "response":
                        # Respuesta real al usuario
                        # Verificar si es un chunk de streaming o mensaje completo
                        is_chunk = details.get("is_chunk", False)

                        if is_chunk and content.strip():
                            # Es un fragmento del streaming del LLM
                            response_text_chunks.append(content)
                        elif not is_chunk and content.strip():
                            # Es un mensaje completo (no streaming)
                            agent_fragments.append({
                                "type": "text",
                                "content": content
                            })

        # ===== CONSOLIDAR RESPUESTA DEL LLM =====
        # Si recibimos chunks de streaming, combinarlos en un solo fragmento de texto
        if response_text_chunks:
            full_response_text = "".join(response_text_chunks)
            agent_fragments.append({
                "type": "text",
                "content": full_response_text
            })
            logger.info("Respuesta LLM consolidada: %d caracteres desde %d chunks", len(full_response_text), len(response_text_chunks))

        # Asegurar que haya al menos un fragmento
        if not agent_fragments:
            agent_fragments.append({
                "type": "text",
                "content": "Respuesta procesada"
            })

        # ===== GUARDAR MENSAJE DEL AGENTE =====
        now = datetime.utcnow()
        agent_msg_dict = {
            "chat_id": chat_id,
            "previous_message_id": user_message_id,
            "user_type": "AGENT",
            "fragments": agent_fragments,
            "created_at": now,
            "updated_at": now
        }

        result = await messages_collection.insert_one(agent_msg_dict)
        agent_message_id = str(result.inserted_id)

        # Actualizar chat con el último mensaje del agente
        await chats_collection.update_one(
            {"_id": ObjectId(chat_id)},
            {"$set": {"last_message_id": agent_message_id, "updated_at": now}}
        )

        logger.info("Mensaje del agente guardado: %s con %d fragmentos",
                    agent_message_id, len(agent_fragments))

        # Notificar finalización exitosa
        yield f"data: {json.dumps({'type': 'done', 'message_id': agent_message_id, 'status': 'success'})}\n\n"

    except Exception as e:
        logger.error("Error en proceso de chat streaming: %s", str(e))
        logger.exception(e)  # Log completo del error
        yield f"data: {json.dumps({'type': 'error', 'content': f'Error interno: {str(e)}'})}\n\n"


@router.post("/send")
async def send_message_with_agent_response(message: MessageCreate) -> StreamingResponse:
    """
    Endpoint principal para enviar mensajes y recibir respuestas del agente.

    Este endpoint acepta un mensaje del usuario, lo procesa con el agente LLM,
    y retorna la respuesta en formato de streaming (Server-Sent Events).

    El formato de streaming permite que el cliente vea la respuesta aparecer
    progresivamente, similar a cómo funciona ChatGPT, mejorando la experiencia
    del usuario al hacer la interacción más dinámica y responsiva.

    Args:
        message: Mensaje del usuario en formato MessageCreate

    Returns:
        StreamingResponse con eventos SSE que contienen los fragmentos de la respuesta

    Raises:
        HTTPException: Si el mensaje no cumple con los requisitos
    """
    # Validar que el mensaje es del usuario
    if message.user_type != "HUMAN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este endpoint solo acepta mensajes de usuario (HUMAN)"
        )

    # Validar que el mensaje contiene exactamente un fragmento de texto
    if not message.fragments or len(message.fragments) != 1 or message.fragments[0].type != "text":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El mensaje debe contener exactamente un fragmento de tipo 'text'"
        )

    user_message = message.fragments[0].content

    # Validar que el mensaje no esté vacío
    if not user_message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El mensaje no puede estar vacío"
        )

    logger.info("Nueva consulta en chat %s: %s...",
                message.chat_id, user_message[:50])

    # Retornar respuesta en streaming
    # Los headers son cruciales para que el streaming funcione correctamente
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


@router.get("/health")
async def health_check():
    """
    Endpoint simple para verificar que el servicio de streaming está funcionando.

    Útil para health checks en entornos de producción o para debugging.
    """
    return {
        "status": "healthy",
        "service": "chat-stream",
        "timestamp": datetime.utcnow().isoformat()
    }

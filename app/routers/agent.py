"""
Project: research-agent
File: app/routers/agent.py
"""
from typing import Any, AsyncGenerator, Dict, List, Optional
import json
import traceback

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langgraph.graph.state import CompiledStateGraph

from app.models.item import ConsultaRequest
from app.graph.graph import GraphState, create_research_graph
from app import logger


router: APIRouter = APIRouter(prefix="/agent", tags=["consulta"])
research_graph : CompiledStateGraph = create_research_graph()


async def generate_response_from_graph(
    userid: str,
    query: str,
    chatid: Optional[str]
) -> AsyncGenerator:
    """
    Ejecuta el grafo y transmite cada mensaje que los nodos emiten
    inmediatamente, sin esperar a que el nodo complete.
    """

    initial_state : GraphState = {
        "query": query,
        "userid": userid,
        "chatid": chatid or "default",
        "messages": [],
        "current_step": "starting",
        "conversation_history": []
    }

    try:
        logger.info("Iniciando procesamiento - User: %s, Query: %s", userid, query)

        # Mensaje inicial
        yield f"data: {json.dumps({'type': 'start', 'content': 'Iniciando procesamiento...'})}\n\n"

        # astream_events captura cada yield de los nodos en tiempo real
        async for event in research_graph.astream_events(initial_state, version="v2"):
            event_type : str = event.get("event")

            # Capturamos eventos de nodos que hacen yield
            if event_type == "on_chain_stream":
                chunk : Dict[str, Any] = event.get("data", {}).get("chunk", {})

                # Extraer información del chunk
                node_name : str = event.get("name", "unknown")
                messages : List = chunk.get("messages", [])
                current_step : str = chunk.get("current_step", "")

                # Enviar cada mensaje inmediatamente
                for message in messages:
                    stream_data : Dict[str, Any] = {
                        "node": node_name,
                        "type": message.get("type", "info"),
                        "content": message.get("content", ""),
                        "details": message.get("details", {}),
                        "step": current_step
                    }

                    json_data : str = json.dumps(stream_data, ensure_ascii=False)
                    yield f"data: {json_data}\n\n"
                    logger.debug("Enviado desde %s: %s...",
                        node_name, message.get('content', '')[:50])

        # Señal de finalización
        logger.info("Procesamiento completado - User: %s", userid)
        data : Dict[str, str] = {
            'type': 'done',
            'content': 'Procesamiento completado',
            'status': 'success'
        }
        yield f"data: {json.dumps(data)}\n\n"
    except (ValueError, KeyError, TypeError, RuntimeError) as e:
        logger.error("Error en procesamiento: %s", str(e))
        traceback.print_exception(e)
        error_data = {
            "type": "error",
            "content": f"Error: {str(e)}",
            "status": "error"
        }
        yield f"data: {json.dumps(error_data)}\n\n"


@router.post("/")
async def consultar(request: ConsultaRequest) -> StreamingResponse:
    """
    Endpoint que retorna respuestas en streaming.
    Cada nodo puede enviar múltiples mensajes durante su ejecución.
    """
    logger.info("Nueva consulta - User: %s, Query: %s", request.userid, request.query)

    return StreamingResponse(
        generate_response_from_graph(
            request.userid,
            request.query,
            request.chatid
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "X-Accel-Buffering": "no"
        }
    )

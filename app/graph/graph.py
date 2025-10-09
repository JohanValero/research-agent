"""
Project: research-agent
File: app/graph/graph.py

Grafo de investigación que integra un LLM real para generar respuestas.
"""
import asyncio
from typing import AsyncGenerator, Optional, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from app.llm.llm_client import llm_client
from app import logger


class GraphState(TypedDict):
    """Estado compartido entre nodos del grafo"""
    query: str
    userid: str
    chatid: str
    messages: list  # Lista simple de diccionarios
    current_step: str
    conversation_history: list  # Historial de la conversación para contexto


async def node_analyze_query(state: GraphState) -> AsyncGenerator:
    """
    Nodo 1: Analiza la consulta del usuario para entender la intención y extraer información clave.

    Este nodo usa el LLM para identificar qué tipo de investigación se necesita,
    qué palabras clave son importantes, y qué enfoque tomar.
    """
    query = state["query"]

    try:
        # Preparar el prompt para el análisis
        system_prompt = """Eres un asistente experto en análisis de consultas. Tu trabajo es:
1. Identificar la intención principal de la consulta
2. Extraer palabras clave importantes
3. Determinar qué tipo de información se necesita buscar
4. Sugerir un enfoque para responder

Responde de forma concisa y estructurada."""

        analysis_prompt = f"""Analiza esta consulta del usuario:
"{query}"

Proporciona:
- Intención principal
- Palabras clave (máximo 5)
- Tipo de información necesaria
- Enfoque sugerido"""

        # Llamar al LLM para obtener el análisis
        analysis_result : Optional[str] = await llm_client.generate_response(
            prompt=analysis_prompt,
            system_prompt=system_prompt,
            temperature=0.3,  # Temperatura baja para respuestas más consistentes
            max_tokens=300
        )

        logger.info("Análisis completado para query: %s", query[:50])

        # Emitir el resultado del análisis
        yield {
            **state,
            "messages": [{
                "type": "thought",
                "content": f"Análisis completado:\n\n{analysis_result}",
                "details": {
                    "query_length": len(query),
                    "step": "analysis_complete"
                }
            }],
            "current_step": "query_analyzed"
        }

    except Exception as e:
        logger.error("Error en análisis: %s", str(e))
        yield {
            **state,
            "messages": [{
                "type": "thought",
                "content": f"Continuando con la consulta original: {query}",
                "details": {"step": "analysis_fallback"}
            }],
            "current_step": "query_analyzed"
        }


async def node_research(state: GraphState) -> AsyncGenerator:
    """
    Nodo 2: Realiza investigación sobre el tema consultado.

    Este nodo simula la búsqueda de información en múltiples fuentes.
    En una implementación completa, aquí podrías integrar búsquedas web,
    consultas a bases de datos vectoriales, o APIs externas.
    """
    query : str = state["query"]

    # Informar inicio de investigación
    yield {
        **state,
        "messages": [{
            "type": "thought",
            "content": f"Iniciando investigación en fuentes disponibles para la consulta {query}",
            "details": {"step": "research_start"}
        }],
        "current_step": "researching"
    }


async def node_generate_response(state: GraphState) -> AsyncGenerator:
    """
    Nodo 3: Genera la respuesta final usando el LLM.

    Este es el nodo principal donde el LLM genera una respuesta comprehensiva
    basada en la consulta del usuario y toda la información recopilada.
    Usa streaming para que el usuario vea la respuesta aparecer progresivamente.
    """
    query = state["query"]

    # Notificar inicio de generación
    yield {
        **state,
        "messages": [{
            "type": "text",
            "content": "Generando respuesta...",
            "details": {"step": "response_preparation"}
        }],
        "current_step": "generating"
    }

    try:
        # Construir el contexto para el LLM
        system_prompt = """Eres un asistente de investigación útil y preciso.
Tu trabajo es proporcionar respuestas detalladas, bien estructuradas y fáciles de entender.
Siempre:
- Responde de forma clara y organizada
- Usa ejemplos cuando sea apropiado
- Si no estás seguro de algo, dilo claramente
- Mantén un tono profesional pero amigable"""

        # Incluir historial de conversación si existe
        conversation_history = state.get("conversation_history", [])

        # Construir mensajes para el LLM
        messages = []
        messages.append({"role": "system", "content": system_prompt})

        # Agregar historial previo si existe
        for hist_msg in conversation_history:
            messages.append(hist_msg)

        # Agregar consulta actual
        messages.append({"role": "user", "content": query})

        # Variable para acumular la respuesta completa
        full_response : str = ""

        # Generar respuesta con streaming
        # El LLM enviará fragmentos de texto a medida que los genera
        async for chunk in llm_client.chat_completion_stream(
            messages=messages,
            temperature=0.7,  # Balance entre creatividad y coherencia
            max_tokens=2000
        ):
            full_response += chunk

            # Emitir cada chunk inmediatamente para streaming en tiempo real
            yield {
                **state,
                "messages": [{
                    "type": "text",
                    "content": chunk,  # Fragmento individual
                    "details": {
                        "step": "streaming_response",
                        "is_chunk": True
                    }
                }],
                "current_step": "generating"
            }

        logger.info("Respuesta generada completamente - longitud: %d caracteres", len(full_response))

        # Mensaje final indicando que la generación terminó
        yield {
            **state,
            "messages": [{
                "type": "text",
                "content": "",  # Vacío porque ya enviamos todo el contenido
                "details": {
                    "step": "response_complete",
                    "total_length": len(full_response),
                    "final": True
                }
            }],
            "current_step": "response_generated"
        }

    except Exception as e:
        logger.error("Error generando respuesta con LLM: %s", str(e))

        # Respuesta de fallback en caso de error
        yield {
            **state,
            "messages": [{
                "type": "text",
                "content": f"Lo siento, ocurrió un error al generar la respuesta. Error: {str(e)}",
                "details": {
                    "step": "response_error",
                    "error": str(e)
                }
            }],
            "current_step": "response_generated"
        }


async def node_finalize(state: GraphState) -> AsyncGenerator:
    """
    Nodo 4: Finaliza el procesamiento con validaciones y formateo.

    Este nodo realiza verificaciones finales de calidad y prepara
    la respuesta para su presentación al usuario.
    """

    # Validación de calidad
    yield {
        **state,
        "messages": [{
            "type": "text",
            "content": "Validando calidad de la respuesta...",
            "details": {"check": "quality", "step": "finalizing"}
        }],
        "current_step": "finalizing"
    }
    await asyncio.sleep(0.3)

    # Procesamiento completado
    yield {
        **state,
        "messages": [{
            "type": "text",
            "content": "Procesamiento completado exitosamente",
            "details": {
                "total_steps": 4,
                "step": "finalization_complete",
                "status": "success"
            }
        }],
        "current_step": "completed"
    }

    logger.info("Procesamiento finalizado para usuario: %s", state.get("userid"))


def create_research_graph() -> CompiledStateGraph:
    """
    Crea el grafo de investigación con integración de LLM real.

    El grafo sigue este flujo:
    1. Análisis de la consulta con LLM
    2. Investigación en fuentes (simulada por ahora)
    3. Generación de respuesta con LLM en streaming
    4. Finalización y validaciones

    Returns:
        Grafo compilado listo para ejecutar
    """
    workflow = StateGraph(GraphState)

    # Registrar todos los nodos
    workflow.add_node("analyze_query", node_analyze_query)
    workflow.add_node("research", node_research)
    workflow.add_node("generate_response", node_generate_response)
    workflow.add_node("finalize", node_finalize)

    # Definir el flujo lineal del grafo
    workflow.set_entry_point("analyze_query")
    workflow.add_edge("analyze_query", "research")
    workflow.add_edge("research", "generate_response")
    workflow.add_edge("generate_response", "finalize")
    workflow.add_edge("finalize", END)

    logger.info("Grafo de investigación con LLM creado")
    return workflow.compile()

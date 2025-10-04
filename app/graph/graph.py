"""
Project: research-agent
File: app/graph/graph.py
"""
import asyncio
from typing import AsyncGenerator, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph


class GraphState(TypedDict):
    """Estado compartido entre nodos del grafo"""
    query: str
    userid: str
    chatid: str
    messages: list  # Lista simple de diccionarios
    current_step: str


async def node_analyze_query(state: GraphState) -> AsyncGenerator:
    """
    Nodo 1: Analiza la consulta con múltiples pasos.
    Cada paso emite un mensaje inmediatamente.
    """
    query = state["query"]

    # Mensaje 1: Iniciando análisis
    yield {
        **state,
        "messages": [{
            "type": "analysis",
            "content": "Iniciando análisis de la consulta...",
            "details": {"step": "analysis_start"}
        }],
        "current_step": "analyzing"
    }
    await asyncio.sleep(0.7)

    # Mensaje 2: Extrayendo palabras clave
    yield {
        **state,
        "messages": [{
            "type": "analysis",
            "content": f"Extrayendo palabras clave de: '{query}'",
            "details": {
                "word_count": len(query.split()),
                "step": "keyword_extraction"
            }
        }],
        "current_step": "analyzing"
    }
    await asyncio.sleep(0.8)

    # Mensaje 3: Análisis completado
    yield {
        **state,
        "messages": [{
            "type": "analysis",
            "content": "Análisis completado",
            "details": {
                "length": len(query),
                "step": "analysis_complete"
            }
        }],
        "current_step": "query_analyzed"
    }


async def node_research(state: GraphState) -> AsyncGenerator:
    """
    Nodo 2: Simula investigación con múltiples fuentes.
    Emite un mensaje por cada fuente consultada.
    """
    sources = ["Base de datos interna", "API externa", "Documentación"]

    for i, source in enumerate(sources, 1):
        yield {
            **state,
            "messages": [{
                "type": "research",
                "content": f"Consultando fuente {i}/3: {source}",
                "details": {
                    "source": source,
                    "progress": f"{i}/3",
                    "step": "researching"
                }
            }],
            "current_step": "researching"
        }
        await asyncio.sleep(2.4)

    # Mensaje final de investigación
    yield {
        **state,
        "messages": [{
            "type": "research",
            "content": "Investigación completada - 3 fuentes consultadas",
            "details": {
                "sources_count": len(sources),
                "step": "research_complete"
            }
        }],
        "current_step": "research_completed"
    }


async def node_generate_response(state: GraphState) -> AsyncGenerator:
    """
    Nodo 3: Genera la respuesta en partes.
    Simula generación incremental de contenido.
    """
    query = state["query"]

    # Parte 1: Preparación
    yield {
        **state,
        "messages": [{
            "type": "response",
            "content": "Preparando estructura de respuesta...",
            "details": {"step": "response_preparation"}
        }],
        "current_step": "generating"
    }
    await asyncio.sleep(1.3)

    # Parte 2: Generación de contenido
    yield {
        **state,
        "messages": [{
            "type": "response",
            "content": "Generando contenido basado en la investigación...",
            "details": {"step": "content_generation"}
        }],
        "current_step": "generating"
    }
    await asyncio.sleep(0.4)

    # Parte 3: Respuesta final
    yield {
        **state,
        "messages": [{
            "type": "response",
            "content": f"Respuesta generada para: '{query}'",
            "details": {
                "userid": state["userid"],
                "step": "response_complete",
                "final_answer": f"Esta es la respuesta simulada para: {query}"
            }
        }],
        "current_step": "response_generated"
    }


async def node_finalize(state: GraphState) -> AsyncGenerator:
    """
    Nodo 4: Finaliza con múltiples pasos de validación.
    """
    checks = ["Validación de calidad",
              "Verificación de seguridad", "Formateo final"]

    for check in checks:
        yield {
            **state,
            "messages": [{
                "type": "finalize",
                "content": f"Ejecutando: {check}",
                "details": {"check": check, "step": "finalizing"}
            }],
            "current_step": "finalizing"
        }
        await asyncio.sleep(0.5)

    # Mensaje final
    yield {
        **state,
        "messages": [{
            "type": "finalize",
            "content": "Procesamiento completado exitosamente",
            "details": {
                "total_steps": 4,
                "step": "finalization_complete",
                "status": "success"
            }
        }],
        "current_step": "completed"
    }


def create_research_graph() -> CompiledStateGraph:
    """
    Crea el grafo de investigación con nodos que emiten
    múltiples mensajes durante su ejecución.
    """
    workflow = StateGraph(GraphState)

    # Agregar nodos
    workflow.add_node("analyze_query", node_analyze_query)
    workflow.add_node("research", node_research)
    workflow.add_node("generate_response", node_generate_response)
    workflow.add_node("finalize", node_finalize)

    # Definir flujo
    workflow.set_entry_point("analyze_query")
    workflow.add_edge("analyze_query", "research")
    workflow.add_edge("research", "generate_response")
    workflow.add_edge("generate_response", "finalize")
    workflow.add_edge("finalize", END)

    return workflow.compile()

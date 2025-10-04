"""
Servidor FastAPI con Streaming para Agente de IA
================================================

Este servidor simula un agente de IA que procesa consultas en múltiples pasos
y reporta su progreso en tiempo real usando Server-Sent Events (SSE).

Para ejecutar:
    pip install fastapi uvicorn
    python servidor_agente.py
    
El servidor estará disponible en http://localhost:8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import AsyncGenerator, Optional
import asyncio
import json
from datetime import datetime
import logging

# Configurar logging para ver qué está pasando en el servidor
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Crear la aplicación FastAPI
app = FastAPI(
    title="Agente IA con Streaming",
    description="Microservicio que procesa consultas complejas y reporta progreso en tiempo real",
    version="1.0.0"
)

# Configurar CORS para permitir peticiones desde el navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica los dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo Pydantic para validar la entrada del usuario


class ConsultaUsuario(BaseModel):
    """
    Modelo que define qué datos esperamos recibir del usuario.
    Pydantic se encargará de validar que los datos sean correctos.
    """
    query: str
    user_id: Optional[str] = "usuario_anonimo"

    class Config:
        """f"""
        schema_extra = {
            "example": {
                "query": "Analiza las ventas del último trimestre",
                "user_id": "usuario_123"
            }
        }


def emitir_evento_sse(tipo: str, mensaje: str, datos: Optional[dict] = None) -> str:
    """
    Formatea un evento en el protocolo Server-Sent Events (SSE).

    El formato SSE es muy específico:
    - Cada línea debe comenzar con "data: "
    - El mensaje completo debe terminar con dos saltos de línea "\n\n"
    - Esto le indica al cliente que el evento está completo

    Args:
        tipo: El tipo de evento (start, step, response, complete, error)
        mensaje: El mensaje descriptivo del evento
        datos: Datos adicionales opcionales en formato diccionario

    Returns:
        String formateado en protocolo SSE
    """
    evento = {
        "type": tipo,
        "message": mensaje,
        "timestamp": datetime.now().isoformat(),
        "data": datos or {}
    }

    # Convertir a JSON y formatear como evento SSE
    json_str = json.dumps(evento, ensure_ascii=False)
    return f"data: {json_str}\n\n"


async def simular_clasificacion_llm(query: str) -> dict:
    """
    Simula la llamada a un LLM para clasificar el tipo de consulta.

    En tu implementación real, aquí harías una llamada a OpenAI, Anthropic,
    o tu LLM preferido para determinar qué tipo de procesamiento necesita
    la consulta del usuario.

    Por ahora, usamos una lógica simple basada en palabras clave.
    """
    # Simular que el LLM toma tiempo en responder
    await asyncio.sleep(1)

    query_lower = query.lower()

    # Detectar saludos
    saludos = ["hola", "hey", "buenos días", "buenas tardes", "hi", "hello"]
    if any(saludo in query_lower for saludo in saludos):
        return {
            "tipo_plan": "respuesta_rapida",
            "confianza": 0.95,
            "razon": "Saludo detectado"
        }

    # Detectar consultas que requieren análisis de datos
    palabras_analisis = ["analiza", "compara",
                         "ventas", "datos", "trimestre", "reporte"]
    if any(palabra in query_lower for palabra in palabras_analisis):
        return {
            "tipo_plan": "respuesta_investigativa",
            "confianza": 0.88,
            "razon": "Requiere análisis de datos"
        }

    # Por defecto, asumir que es investigativa
    return {
        "tipo_plan": "respuesta_investigativa",
        "confianza": 0.70,
        "razon": "Consulta general que podría requerir investigación"
    }


async def ejecutar_plan_rapido(query: str) -> AsyncGenerator[str, None]:
    """
    Ejecuta un plan simple para respuestas rápidas.

    Este generador asíncrono va produciendo eventos usando 'yield'.
    Cada 'yield' envía un evento al cliente inmediatamente.
    """
    logger.info(f"Ejecutando plan rápido para: {query}")

    # Paso 1: Procesando
    yield emitir_evento_sse(
        "step",
        "Procesando saludo y preparando respuesta...",
        {"plan": "rapido", "paso": 1}
    )
    await asyncio.sleep(0.5)

    # Paso 2: Respuesta
    yield emitir_evento_sse(
        "response",
        "¡Hola! Soy tu agente de IA. Estoy aquí para ayudarte con análisis de datos, "
        "consultas SQL, búsqueda en documentos y mucho más. ¿En qué puedo asistirte hoy?",
        {"plan": "rapido", "tiempo_respuesta_segundos": 0.5}
    )

    # Paso 3: Completado
    yield emitir_evento_sse(
        "complete",
        "Plan rápido completado exitosamente",
        {"plan": "rapido"}
    )


async def simular_consulta_sql(query_sql: str, descripcion: str) -> dict:
    """
    Simula la ejecución de una consulta SQL.

    En tu implementación real, aquí conectarías con tu base de datos
    usando asyncpg, aiomysql, o el driver asíncrono correspondiente.
    """
    # Simular tiempo de ejecución de la query
    await asyncio.sleep(2.5)

    # Simular resultados
    return {
        "query_ejecutada": query_sql,
        "filas_afectadas": 1523,
        "tiempo_ejecucion_ms": 2450,
        "columnas": ["categoria", "total_ventas", "promedio"],
        "muestra_resultados": [
            {"categoria": "Electrónica", "total_ventas": 450000, "promedio": 1250},
            {"categoria": "Ropa", "total_ventas": 380000, "promedio": 890},
            {"categoria": "Alimentos", "total_ventas": 520000, "promedio": 650}
        ]
    }


async def simular_busqueda_documentos(terminos: str) -> dict:
    """
    Simula la búsqueda en documentos PDF u otros archivos.

    En tu implementación real, aquí buscarías en tu sistema de archivos,
    base de datos de documentos, o sistema de búsqueda vectorial.
    """
    await asyncio.sleep(2)

    return {
        "terminos_busqueda": terminos,
        "documentos_escaneados": 45,
        "documentos_relevantes": 7,
        "extractos": [
            "Las ventas del Q4 mostraron un crecimiento del 15% respecto al año anterior...",
            "El análisis comparativo indica que la categoría de Electrónica lidera el mercado..."
        ]
    }


async def ejecutar_plan_investigativo(query: str) -> AsyncGenerator[str, None]:
    """
    Ejecuta un plan complejo que simula múltiples pasos de investigación.

    Este es el corazón de tu agente. Aquí orquestas todas las operaciones
    necesarias para responder consultas complejas, y vas reportando cada paso
    al usuario en tiempo real.
    """
    logger.info(f"Ejecutando plan investigativo para: {query}")

    # PASO 1: Análisis inicial
    yield emitir_evento_sse(
        "step",
        "Analizando tu consulta y determinando las fuentes de datos necesarias...",
        {"paso": 1, "total_pasos": 6, "fase": "analisis"}
    )
    await asyncio.sleep(1.5)

    yield emitir_evento_sse(
        "info",
        "Se identificaron 3 fuentes de datos relevantes: Base de datos SQL, "
        "Documentos históricos, y Datos de mercado",
        {"fuentes": ["sql", "documentos", "mercado"]}
    )

    # PASO 2: Primera consulta SQL - Obtener totales
    yield emitir_evento_sse(
        "step",
        "Generando y ejecutando consulta SQL para obtener totales generales...",
        {"paso": 2, "total_pasos": 6, "fase": "sql_query_1"}
    )

    query_sql_1 = "SELECT SUM(monto) as total, COUNT(*) as registros FROM ventas WHERE fecha >= '2024-07-01' AND fecha <= '2024-09-30'"
    resultado_sql_1 = await simular_consulta_sql(query_sql_1, "totales generales")

    yield emitir_evento_sse(
        "sql_ejecutado",
        f"Consulta completada: {resultado_sql_1['filas_afectadas']} registros procesados",
        {
            "query": query_sql_1,
            "resultados": resultado_sql_1
        }
    )

    # PASO 3: Segunda consulta SQL - Datos agrupados
    yield emitir_evento_sse(
        "step",
        "Ejecutando segunda consulta SQL para análisis por categorías...",
        {"paso": 3, "total_pasos": 6, "fase": "sql_query_2"}
    )

    query_sql_2 = "SELECT categoria, SUM(monto) as total, AVG(monto) as promedio FROM ventas GROUP BY categoria ORDER BY total DESC"
    resultado_sql_2 = await simular_consulta_sql(query_sql_2, "agrupación por categoría")

    yield emitir_evento_sse(
        "sql_ejecutado",
        f"Datos agrupados obtenidos: {len(resultado_sql_2['muestra_resultados'])} categorías analizadas",
        {
            "query": query_sql_2,
            "resultados": resultado_sql_2
        }
    )

    # PASO 4: Tercera consulta SQL - Tendencias temporales
    yield emitir_evento_sse(
        "step",
        "Analizando tendencias temporales con tercera consulta SQL...",
        {"paso": 4, "total_pasos": 6, "fase": "sql_query_3"}
    )

    query_sql_3 = "SELECT DATE_TRUNC('week', fecha) as semana, SUM(monto) as total FROM ventas GROUP BY semana ORDER BY semana"
    resultado_sql_3 = await simular_consulta_sql(query_sql_3, "tendencias semanales")

    yield emitir_evento_sse(
        "sql_ejecutado",
        "Tendencias temporales calculadas exitosamente",
        {
            "query": query_sql_3,
            "resultados": resultado_sql_3
        }
    )

    # PASO 5: Búsqueda en documentos
    yield emitir_evento_sse(
        "step",
        "Buscando información contextual en documentos históricos...",
        {"paso": 5, "total_pasos": 6, "fase": "busqueda_documentos"}
    )

    resultado_docs = await simular_busqueda_documentos("ventas trimestre análisis")

    yield emitir_evento_sse(
        "documentos_procesados",
        f"Se escanearon {resultado_docs['documentos_escaneados']} documentos, "
        f"encontrando {resultado_docs['documentos_relevantes']} con información relevante",
        {"resultados": resultado_docs}
    )

    # PASO 6: Síntesis y generación de respuesta
    yield emitir_evento_sse(
        "step",
        "Sintetizando toda la información recopilada y generando respuesta final...",
        {"paso": 6, "total_pasos": 6, "fase": "sintesis"}
    )
    await asyncio.sleep(2)

    # Construir respuesta final basada en los resultados simulados
    respuesta_final = f"""
ANÁLISIS COMPLETO DEL ÚLTIMO TRIMESTRE

📊 RESUMEN EJECUTIVO:
Durante el período analizado (Q3 2024), se procesaron {resultado_sql_1['filas_afectadas']} transacciones 
de ventas. El análisis multifuente revela patrones importantes para la toma de decisiones.

💰 TOTALES Y MÉTRICAS PRINCIPALES:
• Total de registros procesados: {resultado_sql_1['filas_afectadas']:,}
• Tiempo de procesamiento: {resultado_sql_1['tiempo_ejecucion_ms']}ms por consulta

📈 ANÁLISIS POR CATEGORÍAS:
El análisis reveló {len(resultado_sql_2['muestra_resultados'])} categorías principales:
• Electrónica: $450,000 (Promedio: $1,250 por transacción)
• Ropa: $380,000 (Promedio: $890 por transacción)  
• Alimentos: $520,000 (Promedio: $650 por transacción)

La categoría de Alimentos lidera en volumen total, aunque Electrónica tiene el ticket promedio más alto.

📅 TENDENCIAS TEMPORALES:
El análisis semanal muestra un patrón de crecimiento sostenido durante el trimestre,
con picos notables en las últimas semanas del período.

📄 CONTEXTO HISTÓRICO:
La búsqueda en {resultado_docs['documentos_escaneados']} documentos históricos proporcionó 
contexto adicional. Los documentos relevantes indican que este rendimiento está 15% por encima 
del mismo período del año anterior.

✅ CONCLUSIONES Y RECOMENDACIONES:
1. El rendimiento general supera las expectativas establecidas
2. La categoría de Electrónica presenta oportunidad de aumentar volumen
3. Se recomienda analizar las estrategias exitosas de Alimentos para replicarlas
4. Las tendencias semanales sugieren efectividad de las campañas actuales

Este análisis integró datos de múltiples fuentes para proporcionar una visión completa del desempeño.
"""

    yield emitir_evento_sse(
        "response",
        respuesta_final.strip(),
        {
            "plan": "investigativo",
            "consultas_sql_ejecutadas": 3,
            "documentos_consultados": resultado_docs['documentos_escaneados'],
            "tiempo_total_aproximado_segundos": 14
        }
    )

    # Evento final de completado
    yield emitir_evento_sse(
        "complete",
        "Plan investigativo completado exitosamente. Todas las fuentes fueron consultadas.",
        {"plan": "investigativo", "exito": True}
    )


async def orquestador_principal(consulta: ConsultaUsuario) -> AsyncGenerator[str, None]:
    """
    Función principal que orquesta todo el flujo del agente.

    Esta función es como el director de orquesta: decide qué hacer basándose
    en la consulta del usuario y coordina todas las piezas del sistema.
    """
    try:
        logger.info(
            f"Nueva consulta recibida de {consulta.user_id}: {consulta.query}")

        # Evento 1: Inicio
        yield emitir_evento_sse(
            "start",
            "Iniciando procesamiento de tu consulta...",
            {
                "query": consulta.query,
                "user_id": consulta.user_id,
                "timestamp_inicio": datetime.now().isoformat()
            }
        )

        # Evento 2: Clasificación del tipo de plan
        yield emitir_evento_sse(
            "step",
            "Clasificando el tipo de respuesta necesaria usando IA...",
            {"fase": "clasificacion"}
        )

        clasificacion = await simular_clasificacion_llm(consulta.query)

        yield emitir_evento_sse(
            "plan_seleccionado",
            f"Plan seleccionado: {clasificacion['tipo_plan']} (confianza: {clasificacion['confianza']:.0%})",
            clasificacion
        )

        # Evento 3: Ejecutar el plan correspondiente
        if clasificacion['tipo_plan'] == "respuesta_rapida":
            # Para respuestas rápidas, delegamos al generador especializado
            async for evento in ejecutar_plan_rapido(consulta.query):
                yield evento
        else:
            # Para consultas complejas, usamos el plan investigativo
            async for evento in ejecutar_plan_investigativo(consulta.query):
                yield evento

        logger.info(
            f"Consulta completada exitosamente para {consulta.user_id}")

    except Exception as e:
        # Si algo sale mal, enviamos un evento de error
        logger.error(f"Error procesando consulta: {str(e)}", exc_info=True)
        yield emitir_evento_sse(
            "error",
            f"Ocurrió un error durante el procesamiento: {str(e)}",
            {
                "error_tipo": type(e).__name__,
                "error_detalle": str(e)
            }
        )


@app.post("/api/agente/consulta")
async def endpoint_consulta_streaming(consulta: ConsultaUsuario):
    """
    Endpoint principal que recibe consultas y retorna un stream de eventos.

    Este endpoint es especial porque no retorna JSON tradicional, sino un stream
    continuo de eventos Server-Sent Events que el cliente puede consumir en tiempo real.

    Args:
        consulta: Objeto con la query del usuario y metadatos

    Returns:
        StreamingResponse con eventos SSE
    """
    logger.info(
        f"Endpoint /api/agente/consulta llamado con query: {consulta.query}")

    return StreamingResponse(
        orquestador_principal(consulta),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Importante para Nginx
            "Access-Control-Allow-Origin": "*"
        }
    )


@app.get("/api/health")
async def health_check():
    """Endpoint simple para verificar que el servidor está funcionando."""
    return {
        "status": "healthy",
        "servicio": "agente-ia-streaming",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/")
async def root():
    """Página de bienvenida con información sobre el API."""
    return {
        "mensaje": "Bienvenido al Agente de IA con Streaming",
        "documentacion": "/docs",
        "health": "/api/health",
        "endpoint_principal": "POST /api/agente/consulta"
    }


if __name__ == "__main__":
    import uvicorn

    print("="*80)
    print("Iniciando servidor del Agente de IA con Streaming")
    print("="*80)
    print("\nEndpoints disponibles:")
    print("  • http://localhost:8000 - Página de bienvenida")
    print("  • http://localhost:8000/docs - Documentación interactiva")
    print("  • http://localhost:8000/api/health - Health check")
    print("  • POST http://localhost:8000/api/agente/consulta - Endpoint principal\n")
    print("Para probar el servidor, ejecuta cliente_agente.py en otra terminal")
    print("="*80)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

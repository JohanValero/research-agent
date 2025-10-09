"""
Project: research-agent
File: app/llm/llm_client.py

Cliente para interactuar con LM Studio u otros servidores compatibles con OpenAI.
"""
import os
from typing import AsyncGenerator, Iterable, Optional

import openai
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.chat import ChatCompletionMessageParam

from app import logger


class LLMClient:
    """
    Cliente para interactuar con LM Studio o cualquier servidor compatible con OpenAI.

    LM Studio proporciona un servidor local que emula la API de OpenAI, permitiendo
    ejecutar modelos de lenguaje grande localmente sin enviar datos a servicios externos.
    """

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Inicializa el cliente del LLM.

        Args:
            base_url: URL del servidor LM Studio (default: http://localhost:1234/v1)
            api_key: API key (para LM Studio local, puede ser cualquier string)
            model: Nombre del modelo a usar (LM Studio usa el modelo cargado actualmente)
        """
        self.base_url : str = base_url or os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")
        self.api_key : str = api_key or os.getenv("LLM_API_KEY", "lm-studio")
        self.model : str = model or os.getenv("LLM_MODEL", "local-model")

        # Crear cliente asíncrono de OpenAI apuntando a LM Studio
        self.client : AsyncOpenAI = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )

        logger.info("Cliente LLM inicializado - URL: %s, Modelo: %s", self.base_url, self.model)

    async def chat_completion(
        self,
        messages: Iterable[ChatCompletionMessageParam],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> ChatCompletion | AsyncStream[ChatCompletionChunk]:
        """
        Realiza una consulta al LLM sin streaming.

        Args:
            messages: Lista de mensajes en formato OpenAI [{"role": "user", "content": "..."}]
            temperature: Controla la creatividad (0.0 = determinístico, 1.0 = muy creativo)
            max_tokens: Límite de tokens en la respuesta
            stream: Si es True, retorna un generador de streaming

        Returns:
            Respuesta completa del modelo
        """
        try:
            response : ChatCompletion | AsyncStream[ChatCompletionChunk] = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
            )
            return response
        except Exception as e:
            logger.error("Error en chat_completion: %s", str(e))
            raise

    async def chat_completion_stream(
        self,
        messages: Iterable[ChatCompletionMessageParam],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """
        Realiza una consulta al LLM con streaming, emitiendo tokens a medida que se generan.

        Esta función es ideal para crear experiencias interactivas donde el usuario
        ve la respuesta aparecer progresivamente, similar a ChatGPT.

        Args:
            messages: Lista de mensajes en formato OpenAI
            temperature: Controla la creatividad de las respuestas
            max_tokens: Límite de tokens en la respuesta

        Yields:
            Fragmentos de texto (tokens o grupos de tokens) a medida que se generan
        """
        try:
            stream : openai.AsyncStream[ChatCompletionChunk] = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )

            # Procesar cada fragmento del stream
            async for chunk in stream:
                # Extraer el contenido del chunk
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        yield delta.content

        except Exception as e:
            logger.error("Error en chat_completion_stream: %s", str(e))
            raise

    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Optional[str]:
        """
        Método de conveniencia para generar una respuesta simple.

        Args:
            prompt: La pregunta o consulta del usuario
            system_prompt: Instrucciones del sistema para guiar el comportamiento del modelo
            temperature: Controla la creatividad
            max_tokens: Límite de tokens

        Returns:
            Respuesta completa del modelo como string
        """
        messages : Iterable[ChatCompletionMessageParam] = []

        # Agregar system prompt si se proporciona
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Agregar el prompt del usuario
        messages.append({"role": "user", "content": prompt})

        response : ChatCompletion | AsyncStream[ChatCompletionChunk] = await self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False
        )
        assert isinstance(response, ChatCompletion)

        return response.choices[0].message.content

    async def generate_response_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """
        Método de conveniencia para generar una respuesta con streaming.

        Args:
            prompt: La pregunta o consulta del usuario
            system_prompt: Instrucciones del sistema
            temperature: Controla la creatividad
            max_tokens: Límite de tokens

        Yields:
            Fragmentos de texto a medida que se generan
        """
        messages : Iterable[ChatCompletionMessageParam] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        async for chunk in self.chat_completion_stream(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        ):
            yield chunk


# Instancia global del cliente LLM
llm_client = LLMClient()

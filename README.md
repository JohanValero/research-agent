# Research Agent

Sistema de chat con agente de investigación que soporta mensajes con múltiples fragmentos enriquecidos (texto, pensamientos y tablas).

## Arquitectura del Sistema

El sistema utiliza MongoDB con tres colecciones principales:

- **USERS**: Almacena información de usuarios
- **CHATS**: Gestiona conversaciones vinculadas a usuarios mediante `user_id`
- **MESSAGES**: Contiene mensajes enlazados mediante `chat_id` y `previous_message_id`

### Estructura de Datos

#### Usuario
```json
{
  "_id": "ObjectId",
  "username": "string (único)",
  "name": "string",
  "activo": "boolean",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

#### Chat
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId (referencia a USERS)",
  "title": "string",
  "last_message_id": "ObjectId (referencia al último mensaje)",
  "activo": "boolean",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

#### Mensaje
```json
{
  "_id": "ObjectId",
  "chat_id": "ObjectId (referencia a CHATS)",
  "previous_message_id": "ObjectId (referencia al mensaje anterior)",
  "user_type": "HUMAN | AGENT",
  "fragments": [
    {
      "type": "text | thought | table",
      "content": "any"
    }
  ],
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Tipos de Fragmentos

1. **text**: Contenido textual simple
   ```json
   {"type": "text", "content": "Hola, ¿cómo estás?"}
   ```

2. **thought**: Pensamientos internos del agente (colapsables en UI)
   ```json
   {"type": "thought", "content": "Necesito consultar la base de datos"}
   ```

3. **table**: Datos estructurados en formato tabular
   ```json
   {
     "type": "table",
     "content": {
       "headers": ["Nombre", "Email", "Ciudad"],
       "rows": [
         ["Juan", "juan@example.com", "Madrid"],
         ["María", "maria@example.com", "Barcelona"]
       ]
     }
   }
   ```

## Inicio Rápido

### Iniciar el Servidor
```bash
uvicorn app.main:app --reload
```

### Abrir Interfaz Web
Abre `test_client.html` en tu navegador para usar la interfaz gráfica.

## API Endpoints

### Usuarios

#### Crear Usuario
```bash
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "name": "John Doe",
    "activo": true
  }'
```

#### Obtener Usuario
```bash
curl -X GET "http://localhost:8000/users/johndoe"
```

#### Listar Usuarios
```bash
curl -X GET "http://localhost:8000/users/"
```

#### Actualizar Usuario
```bash
curl -X PUT "http://localhost:8000/users/johndoe" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Carlos Doe",
    "activo": true
  }'
```

#### Desactivar Usuario
```bash
curl -X PUT "http://localhost:8000/users/johndoe" \
  -H "Content-Type: application/json" \
  -d '{
    "activo": false
  }'
```

#### Eliminar Usuario
```bash
curl -X DELETE "http://localhost:8000/users/johndoe"
```

### Chats

#### Crear Chat
```bash
curl -X POST "http://localhost:8000/chats/" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "68e0a0d151bbe171cc3a788a",
    "title": "Conversación sobre IA",
    "activo": true
  }'
```

#### Obtener Chat
```bash
curl -X GET "http://localhost:8000/chats/68e0a1234567890abcdef123"
```

#### Listar Chats de un Usuario
```bash
curl -X GET "http://localhost:8000/chats/user/68e0a0d151bbe171cc3a788a"
```

#### Actualizar Chat
```bash
curl -X PUT "http://localhost:8000/chats/68e0a1234567890abcdef123" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Nuevo título del chat"
  }'
```

#### Eliminar Chat
```bash
curl -X DELETE "http://localhost:8000/chats/68e0a1234567890abcdef123"
```

### Mensajes

#### Crear Mensaje Simple (Usuario)
```bash
curl -X POST "http://localhost:8000/messages/" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "68e0a1234567890abcdef123",
    "previous_message_id": null,
    "user_type": "HUMAN",
    "fragments": [
      {
        "type": "text",
        "content": "¿Cuáles son las mejores empresas de tecnología?"
      }
    ]
  }'
```

#### Crear Mensaje Complejo (Agente)
```bash
curl -X POST "http://localhost:8000/messages/" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "68e0a1234567890abcdef123",
    "previous_message_id": "68e0a9999567890abcdef456",
    "user_type": "AGENT",
    "fragments": [
      {
        "type": "text",
        "content": "Basándome en tu pregunta, te ayudaré a conocer las empresas de tecnología."
      },
      {
        "type": "thought",
        "content": "Necesito consultar la base de datos de empresas tech."
      },
      {
        "type": "thought",
        "content": "Se obtuvieron 15 registros. Mostraré los top 3."
      },
      {
        "type": "text",
        "content": "He encontrado las siguientes empresas destacadas:"
      },
      {
        "type": "table",
        "content": {
          "headers": ["Empresa", "Sector", "Empleados", "Valoración"],
          "rows": [
            ["TechCorp", "Cloud Computing", "2500", "Alto"],
            ["DataAI Solutions", "Machine Learning", "850", "Alto"],
            ["InnovateSoft", "SaaS", "1200", "Medio"]
          ]
        }
      },
      {
        "type": "text",
        "content": "¿Te gustaría conocer más detalles sobre alguna de estas empresas?"
      }
    ]
  }'
```

#### Obtener Historial del Chat
Reconstruye la conversación completa siguiendo la cadena de mensajes:
```bash
curl -X GET "http://localhost:8000/messages/chat/68e0a1234567890abcdef123/history"
```

#### Listar Mensajes del Chat (Paginado)
```bash
curl -X GET "http://localhost:8000/messages/chat/68e0a1234567890abcdef123?skip=0&limit=50"
```

#### Obtener Mensaje Específico
```bash
curl -X GET "http://localhost:8000/messages/68e0a7777567890abcdef789"
```

#### Actualizar Fragmentos de Mensaje
```bash
curl -X PUT "http://localhost:8000/messages/68e0a7777567890abcdef789" \
  -H "Content-Type: application/json" \
  -d '{
    "fragments": [
      {
        "type": "text",
        "content": "Contenido actualizado del mensaje"
      }
    ]
  }'
```

#### Eliminar Mensaje
```bash
curl -X DELETE "http://localhost:8000/messages/68e0a7777567890abcdef789"
```

## Agente de Investigación (Streaming)

El agente procesa consultas en tiempo real y retorna eventos mediante Server-Sent Events (SSE).

### Endpoint de Consulta Streaming
```bash
curl -X POST "http://localhost:8000/agent/" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "¿Cómo funciona el machine learning?",
    "userid": "johndoe",
    "chatid": "chat123"
  }'
```

### Respuesta (SSE)
```
data: {"type":"start","content":"Iniciando procesamiento..."}

data: {"node":"analyze_query","type":"analysis","content":"Iniciando análisis...","step":"analyzing"}

data: {"node":"research","type":"research","content":"Consultando fuente 1/3...","step":"researching"}

data: {"type":"done","content":"Procesamiento completado","status":"success"}
```

## Flujo de Trabajo Típico

### 1. Crear Usuario
```bash
# Crear usuario
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "name": "Alice Johnson", "activo": true}'

# Respuesta: {"_id": "68e0a0d151bbe171cc3a788a", "username": "alice", ...}
```

### 2. Crear Chat para el Usuario
```bash
curl -X POST "http://localhost:8000/chats/" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "68e0a0d151bbe171cc3a788a",
    "title": "Mi primera conversación",
    "activo": true
  }'

# Respuesta: {"_id": "68e0a1234567890abcdef123", "user_id": "68e0a0d151bbe171cc3a788a", ...}
```

### 3. Enviar Primer Mensaje (Usuario)
```bash
curl -X POST "http://localhost:8000/messages/" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "68e0a1234567890abcdef123",
    "previous_message_id": null,
    "user_type": "HUMAN",
    "fragments": [{"type": "text", "content": "Hola, necesito ayuda"}]
  }'

# Respuesta: {"_id": "68e0aAAA567890abcdefAAA", ...}
```

### 4. Responder con el Agente
```bash
curl -X POST "http://localhost:8000/messages/" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "68e0a1234567890abcdef123",
    "previous_message_id": "68e0aAAA567890abcdefAAA",
    "user_type": "AGENT",
    "fragments": [
      {"type": "text", "content": "¡Hola! Estoy aquí para ayudarte."},
      {"type": "thought", "content": "Usuario solicitó ayuda general."},
      {"type": "text", "content": "¿En qué puedo asistirte hoy?"}
    ]
  }'
```

### 5. Obtener Historial Completo
```bash
curl -X GET "http://localhost:8000/messages/chat/68e0a1234567890abcdef123/history"
```

## Variables de Entorno

Crear archivo `.env`:
```env
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=research_agent
```

## Estructura del Proyecto

```
research-agent/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── db/
│   │   ├── __init__.py
│   │   └── mongodb.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── chat.py
│   │   ├── message.py
│   │   └── item.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── users.py
│   │   ├── chats.py
│   │   ├── messages.py
│   │   ├── agent.py
│   │   └── items.py
│   └── graph/
│       ├── __init__.py
│       └── graph.py
├── test_client.html
├── .env
├── requirements.txt
└── README.md
```

## Características Principales

- ✅ **Gestión de Usuarios**: CRUD completo con username único
- ✅ **Sistema de Chats**: Conversaciones vinculadas a usuarios
- ✅ **Mensajes Enlazados**: Cadena de mensajes con `previous_message_id`
- ✅ **Fragmentos Enriquecidos**: Texto, pensamientos y tablas en mensajes
- ✅ **Reconstrucción de Historial**: Desde `last_message_id` hacia atrás
- ✅ **Agente con Streaming**: Procesamiento en tiempo real con SSE
- ✅ **Referencias por ObjectId**: Integridad referencial en MongoDB
- ✅ **Interfaz Web**: Clientes HTML para testing y uso

## Dependencias Principales

- FastAPI
- Motor (MongoDB async driver)
- Pydantic v2
- LangGraph
- Python-dotenv

## Notas de Implementación

- Los `_id` son ObjectId de MongoDB convertidos a string en las respuestas
- La cadena de mensajes se construye con `previous_message_id`
- El campo `last_message_id` en chats apunta al mensaje más reciente
- Los fragmentos de tipo `thought` son colapsables en la interfaz web
- El agente usa LangGraph para procesamiento multi-paso

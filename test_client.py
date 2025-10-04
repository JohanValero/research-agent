"""
Project: research-agent
File: test_client.py
"""

import json
import requests

URL = "http://localhost:8000/agent/"

data = {
    "query": "¿Cómo estás?",
    "chatid": "123",
    "userid": "456"
}

response = requests.post(URL, json=data, stream=True, timeout=30)

for line in response.iter_lines():
    if line:
        decoded_line = line.decode('utf-8')
        if decoded_line.startswith('data: '):
            content = decoded_line[6:]  # Remover el prefijo "data: "

            try:
                # Parsear el contenido JSON
                json_content = json.loads(content)

                # Verificar si es la señal de finalización
                if json_content.get('status') == 'done':
                    print("Stream finalizado")
                    break

                # Mostrar el contenido recibido
                if 'content' in json_content:
                    print(json_content['content'])

            except json.JSONDecodeError:
                # Manejar el caso de "[DONE]" u otros mensajes no-JSON
                if content == "[DONE]":
                    print("Stream finalizado")
                    break
                else:
                    print(f"Contenido no-JSON recibido: {content}")

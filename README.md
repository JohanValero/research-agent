Research Agent

uvicorn app.main:app --reload

curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "numero": "123456789",
    "nombre": "Juan Pérez",
    "activo": true
  }'

curl -X GET "http://localhost:8000/users/123456789"

curl -X GET "http://localhost:8000/users/123456789"

curl -X GET "http://localhost:8000/users/"

curl -X PUT "http://localhost:8000/users/123456789" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Juan Carlos Pérez",
    "activo": true
  }'

curl -X PUT "http://localhost:8000/users/123456789" \
  -H "Content-Type: application/json" \
  -d '{
    "activo": false
  }'

curl -X DELETE "http://localhost:8000/users/123456789"
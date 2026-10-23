#!/usr/bin/env bash
set -e

# Activate venv if present
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "✦ Запуск Aboo Perfume Sommelier..."
echo "✦ Web UI & API доступны по адресу: http://localhost:8008"
echo "✦ Swagger документация: http://localhost:8008/docs"

exec uvicorn app.main:app --host 0.0.0.0 --port 8008 --reload

#!/bin/bash
set -e

echo "Starting NG12 Cancer Risk Assessor..."

# Check if vector store is initialized
if [ ! -d "/app/data/vector_store" ] || [ -z "$(ls -A /app/data/vector_store)" ]; then
    echo "Initializing vector store..."
    python scripts/initialize_vector_store.py
else
    echo "Vector store already initialized."
    # Optional: Force re-initialization if needed
    # python scripts/initialize_vector_store.py
fi

# Start the application
echo "Starting Uvicorn server..."
exec python -m uvicorn src.main:app --host 0.0.0.0 --port 8000

#!/bin/bash

echo "🚀 Starting RAG System Demo..."
echo ""

# Check if API is running
API_URL="http://localhost:8000/api/v1/health"
echo "Checking if API is running at $API_URL..."

if curl -s -o /dev/null -w "%{http_code}" "$API_URL" | grep -q "200"; then
    echo "✅ API is running!"
else
    echo "⚠️  API is not running. Starting services..."
    echo ""
    echo "Starting Docker services..."
    cd docker && docker compose up -d
    cd ..
    
    echo "Waiting for services to be ready..."
    sleep 5
    
    echo "Starting API server..."
    source .venv/bin/activate
    uvicorn src.api.main:app --reload &
    API_PID=$!
    
    echo "Waiting for API to be ready..."
    sleep 5
fi

echo ""
echo "🎨 Starting Streamlit UI..."
echo "================================"
echo ""

# Install streamlit dependencies if needed
if ! python -c "import streamlit" 2>/dev/null; then
    echo "Installing Streamlit dependencies..."
    pip install -r requirements-streamlit.txt
fi

# Run Streamlit
streamlit run streamlit_app.py --server.port 8501 --server.address localhost

# Cleanup
if [ ! -z "$API_PID" ]; then
    echo ""
    echo "Stopping API server..."
    kill $API_PID
fi
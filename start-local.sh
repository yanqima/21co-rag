#!/bin/bash

# Local Development Startup Script with Profile Support

PROFILE=${1:-"infra"}

echo "🚀 Starting local RAG development environment with profile: $PROFILE"
echo ""

case $PROFILE in
    "infra")
        echo "📦 Starting infrastructure only (Qdrant + Redis)..."
        docker compose -f docker-compose.local.yml --profile infra up -d
        echo "⏳ Waiting for services to be ready..."
        sleep 15
        echo "✅ Infrastructure services are ready!"
        echo ""
        echo "🔗 Service URLs:"
        echo "   Qdrant: http://localhost:6333"
        echo "   Redis: localhost:6379"
        echo ""
        echo "🏃‍♂️ Now you can run your applications natively:"
        echo "   API: uvicorn src.api.main:app --reload --port 8000"
        echo "   Streamlit: streamlit run streamlit_app.py --server.port 8501"
        ;;
    "apps")
        echo "🐳 Starting applications only (API + Streamlit)..."
        echo "⚠️  Make sure infrastructure is running first!"
        docker compose -f docker-compose.local.yml --profile apps up -d
        ;;
    "full")
        echo "🎯 Starting full stack (Infrastructure + Applications)..."
        docker compose -f docker-compose.local.yml --profile full up -d
        echo "⏳ Waiting for all services to be ready..."
        sleep 20
        echo "✅ All services are ready!"
        echo ""
        echo "🔗 Service URLs:"
        echo "   Streamlit UI: http://localhost:8501"
        echo "   API Docs: http://localhost:8000/docs"
        echo "   Qdrant: http://localhost:6333"
        echo "   Redis: localhost:6379"
        ;;
    *)
        echo "❌ Invalid profile. Available profiles:"
        echo "   infra - Infrastructure only (Qdrant + Redis)"
        echo "   apps  - Applications only (API + Streamlit)"
        echo "   full  - Full stack (Infrastructure + Applications)"
        echo ""
        echo "Usage: $0 [infra|apps|full]"
        exit 1
        ;;
esac

echo ""
echo "📋 Make sure you have .env configured for local development"
echo "🔧 To stop services: docker compose -f docker-compose.local.yml --profile $PROFILE down"

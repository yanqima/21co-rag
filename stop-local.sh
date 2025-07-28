#!/bin/bash

# Stop Local Development Services

PROFILE=${1:-"infra"}

echo "🛑 Stopping local RAG services with profile: $PROFILE"

case $PROFILE in
    "infra")
        echo "📦 Stopping infrastructure services..."
        docker compose -f docker-compose.local.yml --profile infra down
        ;;
    "apps")
        echo "🐳 Stopping application services..."
        docker compose -f docker-compose.local.yml --profile apps down
        ;;
    "full")
        echo "🎯 Stopping all services..."
        docker compose -f docker-compose.local.yml --profile full down
        ;;
    "all")
        echo "🧹 Stopping all services and removing volumes..."
        docker compose -f docker-compose.local.yml down --volumes
        ;;
    *)
        echo "❌ Invalid profile. Available profiles:"
        echo "   infra - Stop infrastructure only"
        echo "   apps  - Stop applications only"
        echo "   full  - Stop all services"
        echo "   all   - Stop all services and remove volumes"
        echo ""
        echo "Usage: $0 [infra|apps|full|all]"
        exit 1
        ;;
esac

echo "✅ Services stopped!"

#!/bin/bash

# GCP Cloud Run Deployment Script
# Make sure you have gcloud CLI installed and authenticated
#
# Configuration Options:
# 1. Create a .env.deploy file with your deployment parameters (recommended)
#    - Copy deploy.config.example to .env.deploy and update the values
# 2. Set environment variables before running the script:
#    - export PROJECT_ID="your-project-id"
#    - export REGION="your-region" 
#    - export SERVICE_NAME_API="your-api-service-name"
#    - export SERVICE_NAME_STREAMLIT="your-streamlit-service-name"
# 3. Let the script prompt you for values (uses defaults if you press Enter)

# Function to prompt for input with a default value
prompt_with_default() {
    local var_name=$1
    local prompt_text=$2
    local default_value=$3
    
    if [ -z "${!var_name}" ]; then
        read -p "$prompt_text [$default_value]: " input_value
        if [ -z "$input_value" ]; then
            export $var_name="$default_value"
        else
            export $var_name="$input_value"
        fi
    fi
    echo "Using $var_name: ${!var_name}"
}

# Check for .env.deploy file and source it if it exists
if [ -f ".env.deploy" ]; then
    echo "📋 Loading deployment configuration from .env.deploy..."
    source .env.deploy
fi

echo "🚀 Deploying RAG System to GCP Cloud Run..."
echo "⚙️  Setting up deployment parameters..."

# Prompt for deployment parameters if not already set
prompt_with_default "PROJECT_ID" "Enter your GCP Project ID" "nifty-charter-464916-f6"
prompt_with_default "REGION" "Enter your GCP Region" "europe-west1"
prompt_with_default "SERVICE_NAME_API" "Enter API service name" "rag-api"
prompt_with_default "SERVICE_NAME_STREAMLIT" "Enter Streamlit service name" "rag-streamlit"

echo ""
echo "📋 Deployment Configuration:"
echo "   Project ID: $PROJECT_ID"
echo "   Region: $REGION"
echo "   API Service: $SERVICE_NAME_API"
echo "   Streamlit Service: $SERVICE_NAME_STREAMLIT"
echo ""

# Ask for confirmation
read -p "Proceed with deployment? (y/N): " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled."
    exit 1
fi

# Set project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "📋 Enabling required GCP APIs..."
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable redis.googleapis.com

# Build and deploy API service
echo "🔨 Building and deploying API service..."
# Load environment variables from .env.gcp
source .env.gcp
# Copy Dockerfile for Cloud Run deployment
cp Dockerfile.cloudrun Dockerfile
gcloud run deploy $SERVICE_NAME_API \
    --source . \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --vpc-connector rag-connector \
    --set-env-vars OPENAI_API_KEY="$OPENAI_API_KEY",OPENAI_MODEL="$OPENAI_MODEL",ENVIRONMENT="$ENVIRONMENT",QDRANT_URL="$QDRANT_URL",QDRANT_API_KEY="$QDRANT_API_KEY",QDRANT_COLLECTION="$QDRANT_COLLECTION",API_HOST="$API_HOST",API_PORT="$API_PORT",LOG_LEVEL="$LOG_LEVEL",REDIS_HOST="$REDIS_HOST",REDIS_PORT="$REDIS_PORT",REDIS_DB="$REDIS_DB",EMBEDDING_MODEL="$EMBEDDING_MODEL",EMBEDDING_DIMENSION="$EMBEDDING_DIMENSION"

# Build and deploy Streamlit service
echo "🎨 Building and deploying Streamlit service..."
# Copy Dockerfile for Streamlit deployment
cp Dockerfile.streamlit Dockerfile
gcloud run deploy $SERVICE_NAME_STREAMLIT \
    --source . \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --port 8080 \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 5 \
    --set-env-vars ENVIRONMENT="$ENVIRONMENT",API_HOST="rag-api-479524373755.europe-west1.run.app",API_PORT="443",API_PROTOCOL="https"

echo "✅ Deployment complete!"
echo "📝 Remember to:"
echo "   1. Set up Qdrant Cloud and update QDRANT_URL and QDRANT_API_KEY in .env.gcp"
echo "   2. Create Cloud Memorystore Redis instance and update REDIS_HOST in .env.gcp"
echo "   3. Set your OpenAI API key in .env.gcp"
echo "   4. For easier future deployments, copy deploy.config.example to .env.deploy and update with your values"
cp Dockerfile.cloudrun Dockerfile

#!/bin/bash

# GCP Cloud Run Deployment Script
# Make sure you have gcloud CLI installed and authenticated

PROJECT_ID="nifty-charter-464916-f6"  # Replace with your actual project ID
REGION="europe-west1"
SERVICE_NAME_API="rag-api"
SERVICE_NAME_STREAMLIT="rag-streamlit"

echo "🚀 Deploying RAG System to GCP Cloud Run..."

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
    --port 8080 \
    --memory 2Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --set-env-vars OPENAI_API_KEY="$OPENAI_API_KEY",OPENAI_MODEL="$OPENAI_MODEL",ENVIRONMENT="$ENVIRONMENT",QDRANT_URL="$QDRANT_URL",QDRANT_API_KEY="$QDRANT_API_KEY",QDRANT_COLLECTION="$QDRANT_COLLECTION",API_HOST="$API_HOST",API_PORT="$API_PORT",LOG_LEVEL="$LOG_LEVEL",PORT="$PORT"

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
    --set-env-vars OPENAI_API_KEY="$OPENAI_API_KEY",OPENAI_MODEL="$OPENAI_MODEL",ENVIRONMENT="$ENVIRONMENT",QDRANT_URL="$QDRANT_URL",QDRANT_API_KEY="$QDRANT_API_KEY",QDRANT_COLLECTION="$QDRANT_COLLECTION",API_HOST="$API_HOST",API_PORT="$API_PORT",LOG_LEVEL="$LOG_LEVEL",PORT="$PORT"

echo "✅ Deployment complete!"
echo "📝 Remember to:"
echo "   1. Set up Qdrant Cloud and update QDRANT_URL and QDRANT_API_KEY in .env.gcp"
echo "   2. Create Cloud Memorystore Redis instance and update REDIS_HOST in .env.gcp"
echo "   3. Update PROJECT_ID in this script"
echo "   4. Set your OpenAI API key in .env.gcp"

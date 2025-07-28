#!/bin/bash

# GCP Cloud Run Deployment Script
# Make sure you have gcloud CLI installed and authenticated

PROJECT_ID="your-gcp-project-id"
REGION="us-central1"
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
gcloud run deploy $SERVICE_NAME_API \
    --source . \
    --dockerfile Dockerfile.cloudrun \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --port 8080 \
    --memory 2Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --env-vars-file .env.gcp

# Build and deploy Streamlit service
echo "🎨 Building and deploying Streamlit service..."
gcloud run deploy $SERVICE_NAME_STREAMLIT \
    --source . \
    --dockerfile Dockerfile.cloudrun \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --port 8080 \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 5 \
    --env-vars-file .env.gcp \
    --command "streamlit,run,streamlit_app.py,--server.port=8080,--server.address=0.0.0.0"

echo "✅ Deployment complete!"
echo "📝 Remember to:"
echo "   1. Set up Qdrant Cloud and update QDRANT_URL and QDRANT_API_KEY in .env.gcp"
echo "   2. Create Cloud Memorystore Redis instance and update REDIS_HOST in .env.gcp"
echo "   3. Update PROJECT_ID in this script"
echo "   4. Set your OpenAI API key in .env.gcp"

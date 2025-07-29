# Dockerfile optimized for Streamlit on Cloud Run
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY sample_data/ ./sample_data/
COPY streamlit_app.py .

# Create directories
RUN mkdir -p /app/logs /app/data

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Use PORT environment variable for Cloud Run
ENV PORT=8080
EXPOSE $PORT

# Streamlit command
CMD exec streamlit run streamlit_app.py --server.port=$PORT --server.address=0.0.0.0

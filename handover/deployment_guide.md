# Deployment Guide

## Prerequisites

- AWS Account with appropriate permissions
- Docker installed locally
- AWS CLI configured
- Domain name (optional, for HTTPS)

## AWS ECS Deployment

### 1. Build and Push Docker Image

```bash
# Build the image
docker build -f docker/Dockerfile -t rag-api:latest .

# Tag for ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin [YOUR_ECR_URI]
docker tag rag-api:latest [YOUR_ECR_URI]/rag-api:latest

# Push to ECR
docker push [YOUR_ECR_URI]/rag-api:latest
```

### 2. Create ECS Task Definition

Create `ecs-task-definition.json`:

```json
{
  "family": "rag-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "rag-api",
      "image": "[YOUR_ECR_URI]/rag-api:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "QDRANT_HOST", "value": "qdrant.internal"},
        {"name": "REDIS_HOST", "value": "redis.internal"}
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:openai-api-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/rag-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### 3. Deploy Qdrant on ECS

```yaml
# qdrant-task-definition.json
{
  "family": "qdrant",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "qdrant",
      "image": "qdrant/qdrant:latest",
      "portMappings": [
        {
          "containerPort": 6333,
          "protocol": "tcp"
        }
      ],
      "mountPoints": [
        {
          "sourceVolume": "qdrant-storage",
          "containerPath": "/qdrant/storage"
        }
      ]
    }
  ],
  "volumes": [
    {
      "name": "qdrant-storage",
      "efsVolumeConfiguration": {
        "fileSystemId": "fs-xxxxxxxx"
      }
    }
  ]
}
```

### 4. Set up Application Load Balancer

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name rag-api-alb \
  --subnets subnet-xxx subnet-yyy \
  --security-groups sg-xxxxxxxx

# Create target group
aws elbv2 create-target-group \
  --name rag-api-targets \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-xxxxxxxx \
  --target-type ip \
  --health-check-path /api/v1/health
```

### 5. Create ECS Service

```bash
aws ecs create-service \
  --cluster your-cluster \
  --service-name rag-api \
  --task-definition rag-api:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx]}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=rag-api,containerPort=8000"
```

## Kubernetes Deployment

### 1. Create Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: rag-system
```

### 2. Deploy Qdrant

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: qdrant
  namespace: rag-system
spec:
  serviceName: qdrant
  replicas: 1
  selector:
    matchLabels:
      app: qdrant
  template:
    metadata:
      labels:
        app: qdrant
    spec:
      containers:
      - name: qdrant
        image: qdrant/qdrant:latest
        ports:
        - containerPort: 6333
        volumeMounts:
        - name: storage
          mountPath: /qdrant/storage
  volumeClaimTemplates:
  - metadata:
      name: storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
```

### 3. Deploy RAG API

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-api
  namespace: rag-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rag-api
  template:
    metadata:
      labels:
        app: rag-api
    spec:
      containers:
      - name: api
        image: your-registry/rag-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: QDRANT_HOST
          value: qdrant
        - name: REDIS_HOST
          value: redis
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: rag-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
```

## Monitoring Setup

### 1. Prometheus Configuration

```yaml
# prometheus-config.yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'rag-api'
    static_configs:
      - targets: ['rag-api:8000']
    metrics_path: '/api/v1/metrics'
```

### 2. Grafana Dashboard

Import the provided dashboard JSON or create custom panels for:
- Request rate and latency
- Document processing metrics
- Vector search performance
- Error rates and alerts

## Production Checklist

- [ ] SSL/TLS certificates configured
- [ ] Database backups scheduled
- [ ] Monitoring alerts configured
- [ ] Log aggregation set up
- [ ] Auto-scaling policies defined
- [ ] Security groups reviewed
- [ ] API rate limiting tested
- [ ] Disaster recovery plan documented

## Troubleshooting

### Common Issues

1. **Vector dimension mismatch**
   - Ensure EMBEDDING_DIMENSION matches your model
   - Recreate collection if changing dimensions

2. **High memory usage**
   - Adjust batch sizes in configuration
   - Scale horizontally rather than vertically

3. **Slow queries**
   - Check Qdrant index optimization
   - Consider adding Redis caching layer

### Health Checks

```bash
# Check API health
curl http://your-domain/api/v1/health

# Check metrics
curl http://your-domain/api/v1/metrics

# Test document processing
curl -X POST http://your-domain/api/v1/ingest \
  -F "file=@sample.pdf"
```
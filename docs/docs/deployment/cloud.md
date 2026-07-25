# Cloud Deployment

## AWS ECS

```bash
# Build and push to ECR
aws ecr create-repository --repository-name amf-backend
docker tag amf-backend:latest $AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com/amf-backend:latest
docker push $AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com/amf-backend:latest

# Create ECS service (use AWS console or CLI)
aws ecs create-service \
  --cluster amf-cluster \
  --service-name amf-backend \
  --task-definition amf-backend:1 \
  --desired-count 2 \
  --launch-type FARGATE
```

## Google Cloud Run

```bash
gcloud run deploy amf-backend \
  --image ghcr.io/amf/backend:latest \
  --set-env-vars "AMF_ENVIRONMENT=production,AMF_DEBUG=false" \
  --memory 512Mi \
  --cpu 1 \
  --port 8000 \
  --min-instances 1 \
  --max-instances 10 \
  --region us-central1
```

## Azure Container Apps

```bash
az containerapp create \
  --name amf-backend \
  --resource-group amf-rg \
  --image ghcr.io/amf/backend:latest \
  --environment amf-env \
  --env-vars AMF_ENVIRONMENT=production AMF_DEBUG=false \
  --ingress external \
  --target-port 8000 \
  --cpu 1 \
  --memory 2Gi \
  --min-replicas 1 \
  --max-replicas 5
```

## Best Practices

1. **Use managed SSL** — Cloud LB + Let's Encrypt / AWS ACM
2. **Enable auto-scaling** — Scale based on CPU/memory
3. **Use managed databases** — RDS, Cloud SQL, Cosmos DB
4. **Monitor costs** — Set budget alerts
5. **Backup config** — Store in parameter store or secrets manager

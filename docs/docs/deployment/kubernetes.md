# Kubernetes Deployment

## Prerequisites

- Kubernetes 1.28+
- kubectl configured
- Container registry access

## Deployment Files

### Backend Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: amf-backend
  labels:
    app: amf-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: amf-backend
  template:
    metadata:
      labels:
        app: amf-backend
    spec:
      containers:
      - name: backend
        image: ghcr.io/amf/backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: AMF_ENVIRONMENT
          value: "production"
        - name: AMF_DEBUG
          value: "false"
        - name: AMF_ALLOWED_ORIGINS
          value: "https://amf.example.com"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 3
          periodSeconds: 5
```

### Backend Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: amf-backend
spec:
  selector:
    app: amf-backend
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

### Frontend Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: amf-frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: amf-frontend
  template:
    metadata:
      labels:
        app: amf-frontend
    spec:
      containers:
      - name: frontend
        image: ghcr.io/amf/frontend:latest
        ports:
        - containerPort: 3000
        env:
        - name: NEXT_PUBLIC_API_URL
          value: "https://api.amf.example.com"
```

### Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: amf-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - amf.example.com
    - api.amf.example.com
    secretName: amf-tls
  rules:
  - host: amf.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: amf-frontend
            port:
              number: 3000
  - host: api.amf.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: amf-backend
            port:
              number: 8000
```

## Helm Chart (Coming Soon)

```bash
helm repo add amf https://charts.amf.dev
helm install amf amf/amf
```

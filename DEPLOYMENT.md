# Production Deployment Guide

## Quick Start - Docker Compose

```bash
# 1. Set up environment
cp .env.example .env
# Edit .env with production secrets

# 2. Build and run
docker-compose -f docker-compose.prod.yml up -d

# 3. Check status
docker-compose -f docker-compose.prod.yml ps
```

## Kubernetes Deployment

### Prerequisites
- kubectl configured
- cert-manager installed (`helm install cert-manager jetstack/cert-manager`)
- nginx-ingress installed

### Deploy
```bash
# Create namespace and secrets
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secret.yaml

# Create ConfigMap
kubectl apply -f k8s/configmap.yaml

# Deploy application
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/poddisruptionbudget.yaml
kubectl apply -f k8s/ingress.yaml

# Wait for rollout
kubectl rollout status deployment/bsgateway-api -n bsgateway
```

### Verify
```bash
# Check pods
kubectl get pods -n bsgateway

# Check logs
kubectl logs -n bsgateway deployment/bsgateway-api

# Check ingress
kubectl get ingress -n bsgateway
```

## Production Checklist

- [ ] Set strong passwords for PostgreSQL, Redis, JWT
- [ ] Update DNS to point to nginx/ingress IP
- [ ] Verify SSL certificates (auto via cert-manager)
- [ ] Configure backup for PostgreSQL
- [ ] Set up monitoring (Prometheus + Grafana)
- [ ] Configure log aggregation (ELK/Loki)
- [ ] Enable rate limiting
- [ ] Set resource limits and requests
- [ ] Configure auto-scaling (HPA)

## Monitoring

### Health Checks
- API: `GET /health`
- Database: PostgreSQL healthcheck
- Cache: Redis healthcheck

### Metrics
```bash
# Prometheus metrics (add to deployment)
# /metrics endpoint (uvicorn with prometheus-client)
```

## Scaling

### Horizontal Scaling
```bash
# Kubernetes
kubectl scale deployment bsgateway-api -n bsgateway --replicas=5

# Docker Compose (use swarm mode)
docker stack deploy -c docker-compose.prod.yml bsgateway
```

### Vertical Scaling
Update resource limits in deployment.yaml and reapply.

## Disaster Recovery

### Database Backup
```bash
# PostgreSQL
pg_dump -h postgres -U bsgateway bsgateway > backup.sql
```

### Redis Persistence
Redis uses AOF (append-only file) by default in docker-compose.prod.yml.

## Troubleshooting

### API not responding
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs api

# Restart service
docker-compose -f docker-compose.prod.yml restart api
```

### Database connection errors
```bash
# Test PostgreSQL connection
docker-compose -f docker-compose.prod.yml exec postgres pg_isready
```

### TLS certificate issues
```bash
# Check cert-manager
kubectl describe certificate -n bsgateway bsgateway-tls
kubectl describe clusterissuer letsencrypt-prod
```

## Performance Tuning

### Database
- Connection pooling: 10-50 connections
- Query caching: 5-15 min TTL
- Index optimization

### Cache
- Redis maxmemory-policy: allkeys-lru
- TTL: 5-300 seconds by feature

### Application
- Worker processes: CPU count
- Thread pools: 10-50 threads

## Security

### Network Policies
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: bsgateway-netpol
  namespace: bsgateway
spec:
  podSelector:
    matchLabels:
      app: bsgateway-api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          ingress: "true"
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
  - to:
    - podSelector:
        matchLabels:
          app: redis
  - to:
    - namespaceSelector: {}
      podSelector:
        matchLabels:
          k8s-app: kube-dns

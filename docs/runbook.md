# Operations Runbook — The Smooth Operator

Instructions and commands for deploying and operating the Smooth Operator outreach engine.

## Local Development Setup

1. Copy `.env.example` to `.env` and fill in API keys:
   ```bash
   cp .env.example .env
   ```

2. Start the local Docker Compose stack:
   ```bash
   docker compose up -d
   ```
   This will spin up:
   * **API**: `http://localhost:8000`
   * **PostgreSQL**: Port `5432`
   * **Redis**: Port `6379`
   * **ChromaDB**: Port `8100`
   * **Grafana**: `http://localhost:3000`
   * **Prometheus**: `http://localhost:9090`
   * **Prefect**: `http://localhost:4200`

## Kubernetes Deployment

Deploy manifests to the cluster namespace:
```bash
kubectl apply -f infrastructure/k8s/namespace.yaml
kubectl apply -f infrastructure/k8s/
```

Verify pods are running:
```bash
kubectl get pods -n smooth-operator
```

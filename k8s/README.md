# Kubernetes manifests

Raw manifests for deploying the stack to a cluster. A templated **Helm chart**
(with values for dev/prod, ingress, and autoscaling) follows in `charts/`.

## Layout
| File | Contents |
|---|---|
| `api.yaml` | FastAPI backend — Deployment (2 replicas, `/readyz` + `/health` probes) + Service on 8000 |
| `web.yaml` | Next.js frontend — Deployment + Service on 3000 |
| `datastores.yaml` | Qdrant, Neo4j, Postgres — StatefulSets with PVCs + headless Services (stable DNS) |

Services use plain names (`api`, `web`, `qdrant`, `neo4j`, `postgres`) so
in-cluster DNS matches the env wiring the app expects.

## Apply (any cluster: kind / minikube / real)
```bash
# Build + load images first (kind example):
docker build -t agentic-ai-os-api:latest .
docker build -t agentic-ai-os-web:latest ./frontend
kind load docker-image agentic-ai-os-api:latest agentic-ai-os-web:latest

kubectl apply -f k8s/
kubectl get pods,svc
kubectl port-forward svc/web 3000:3000    # then open http://localhost:3000
```

## Notes
- Secrets (API keys, DB creds) are inline placeholders here for readability; the
  Helm chart moves them to `Secret`/`ConfigMap` (Day 26).
- Ingress + HPA (autoscaling) land on Day 27; a kind smoke-deploy in CI on Day 28.
- Validated structurally by `tests/test_k8s_manifests.py` (kubeconform-style
  checks) so the YAML can't silently drift.

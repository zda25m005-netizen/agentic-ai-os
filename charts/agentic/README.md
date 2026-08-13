# agentic-ai-os Helm chart

Templated deployment of the full stack (API, web, and the three datastores) with
per-environment values.

## Install / render / lint
```bash
helm lint charts/agentic
helm template agentic charts/agentic          # render manifests to stdout
helm install agentic charts/agentic           # deploy to the current context
helm upgrade agentic charts/agentic -f prod-values.yaml
```

## Values reference
| Key | Default | Meaning |
|---|---|---|
| `image.pullPolicy` | `IfNotPresent` | Image pull policy for all pods |
| `api.image` | `agentic-ai-os-api:latest` | Backend image |
| `api.replicas` | `2` | Backend replica count |
| `api.port` | `8000` | Backend container/service port |
| `api.env` | (map) | Env vars (QDRANT_URL, NEO4J_URI, DATABASE_URL) |
| `api.resources` | requests/limits | CPU/memory requests + limits |
| `web.image` | `agentic-ai-os-web:latest` | Frontend image |
| `web.replicas` | `2` | Frontend replica count |
| `web.port` | `3000` | Frontend port |
| `web.apiBase` | `http://api:8000` | Browser-facing API base URL |
| `datastores.qdrant.image` / `.storage` | `qdrant/qdrant:latest` / `5Gi` | Vector DB image + PVC size |
| `datastores.neo4j.image` / `.storage` / `.auth` | `neo4j:5-community` / `5Gi` / `neo4j/neo4jpassword` | Graph DB |
| `datastores.postgres.image` / `.storage` / creds | `postgres:16-alpine` / `5Gi` | Memory DB |
| `ingress.enabled` / `ingress.host` | `false` / `agentic.local` | Ingress toggle + host (Day 27) |

## Notes
- Secrets are plain values here for readability; move them to a `Secret` in prod
  (Day 26 adds ConfigMap/Secret support).
- Structure is validated by `tests/test_helm_chart.py`; run `helm lint` locally
  for the full check.

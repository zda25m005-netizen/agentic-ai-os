# Deploy Runbook

Three ways the stack runs: Docker Compose (dev), a local Kubernetes cluster
(kind), and a real cluster via the Helm chart. CI proves the k8s path on every
push.

## Local kind cluster (one command)
```bash
make k8s-up      # create kind cluster, build + load images, helm install
kubectl get pods,svc
kubectl port-forward svc/web 3000:3000   # open http://localhost:3000
make k8s-down    # tear it all down
```

## CI verification (automatic)
- **`.github/workflows/ci.yml`** — ruff lint + pytest on every push/PR.
- **`.github/workflows/k8s-smoke.yml`** — spins up a kind cluster, builds + loads
  the images, `helm install`s the chart, waits for the API rollout, and curls
  `/health` (asserts `{"status":"ok"}`). This turns the deploy from
  "structurally valid" into "actually boots and serves."
- **`.github/workflows/release-images.yml`** — on a `v*` tag, builds and pushes
  the API + web images to GHCR (`ghcr.io/<repo>-api`, `-web`).

## Real cluster (Helm)
```bash
# Tag a release to publish images:
git tag v1.0.0 && git push --tags        # release-images workflow -> GHCR

helm upgrade --install agentic charts/agentic \
  -f charts/agentic/values-prod.yaml \
  --set api.image=ghcr.io/<owner>/agentic-ai-os-api:v1.0.0 \
  --set web.image=ghcr.io/<owner>/agentic-ai-os-web:v1.0.0 \
  --set secrets.OPENAI_API_KEY="$OPENAI_API_KEY" \
  --set secrets.JWT_SECRET="$JWT_SECRET"
```
Prod values enable the Ingress and the API HPA. For real secrets, prefer an
external secret manager over `--set` (see [charts/agentic/README.md](../charts/agentic/README.md)).

## Rollback
```bash
helm history agentic
helm rollback agentic <REVISION>
```

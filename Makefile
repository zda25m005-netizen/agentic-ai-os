.PHONY: install run lint fmt test eval ablation graph-eval rerank-eval dpo-export sft-data lora-merge lora-plot lora-eval lora-report k8s-up k8s-down clean

install:
	pip install -e ".[dev]"
	pre-commit install || true

run:
	uvicorn app.api.main:app --reload --port 8000

lint:
	ruff check .

fmt:
	ruff format .
	ruff check --fix .

test:
	pytest -q

eval:
	python -m eval.run

ablation:
	python -m eval.ablation

graph-eval:
	python -m eval.graph_eval

rerank-eval:
	python -m eval.reranker_eval

dpo-export:
	python -m app.feedback.dpo_cli

sft-data:
	python -m app.finetune.build_dataset

lora-merge:
	python -m app.finetune.merge

lora-plot:
	python -m app.finetune.report

lora-eval:
	python -m eval.finetune_runner

lora-report:
	python -m app.finetune.ablation

k8s-up:
	kind create cluster --name agentic || true
	docker build -t agentic-ai-os-api:dev .
	docker build -t agentic-ai-os-web:dev ./frontend
	kind load docker-image agentic-ai-os-api:dev agentic-ai-os-web:dev --name agentic
	helm upgrade --install agentic charts/agentic \
		--set api.image=agentic-ai-os-api:dev \
		--set web.image=agentic-ai-os-web:dev \
		--set image.pullPolicy=Never

k8s-down:
	kind delete cluster --name agentic

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache

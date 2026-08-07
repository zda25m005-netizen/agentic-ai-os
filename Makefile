.PHONY: install run lint fmt test eval ablation graph-eval dpo-export clean

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

dpo-export:
	python -m app.feedback.dpo_cli

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache

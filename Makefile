.PHONY: install run lint fmt test eval clean

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
	@echo "Eval harness lands in Week 3 (Day 21). Placeholder for now."

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache

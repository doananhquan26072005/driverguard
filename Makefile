.PHONY: venv run test lint format typecheck check clean frontend-test

PY_DIRS = edge_agent/ backend/ tools/ tests/

# Python 3.12 venv with DriverGuard runtime + dev tools (course template: requirements-template.txt)
venv:
	uv venv -p 3.12 --seed .venv
	uv pip install --python .venv/bin/python -r requirements-dev.txt


run:
	uvicorn backend.app:app --reload --port 8100

test:
	pytest tests/ -v

lint:
	ruff check $(PY_DIRS)

format:
	ruff format $(PY_DIRS)

typecheck:
	cd frontend && npm run typecheck

frontend-test:
	cd frontend && npm test

check: lint format test

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +

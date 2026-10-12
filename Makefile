.PHONY: venv run test coverage lint format typecheck check clean frontend-test

PY_DIRS = edge_agent/ backend/ tools/ tests/

# Python 3.12 venv with DriverGuard runtime + dev tools (course template: requirements-template.txt)
venv:
	uv venv -p 3.12 --seed .venv
	uv pip install --python .venv/bin/python -r requirements-dev.txt


run:
	uvicorn backend.app:app --reload --port 8100

test:
	pytest tests/ -v

# Line coverage of the three DriverGuard packages (table in eval/results/report.md section 4)
coverage:
	pytest tests/ -q --cov=edge_agent --cov=backend --cov=tools --cov-report=term

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
	rm -f .coverage

run:
	rye run uvicorn src.main:app --reload --port 8000

lint/check:
	rye run ruff check .

lint/format:
	rye run ruff check --fix .

lint/ci:
	@echo "Running linter with all rules including type hints..."
	ruff check . --ignore I
	@echo "Showing type hint issues only (for reference)..."
	ruff check . --select ANN --statistics || true
	ruff format . --diff

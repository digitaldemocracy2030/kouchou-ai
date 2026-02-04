run:
	rye run uvicorn src.main:app --reload --port 8000

lint/check:
	rye run ruff check .

lint/format:
	rye run ruff check --fix .

lint/ci:
	@echo "Running linter with all rules including type hints..."
	rye run ruff check . --ignore I
	@echo "Showing type hint issues only (for reference)..."
	rye run ruff check . --select ANN --statistics || true
	rye run ruff format . --diff

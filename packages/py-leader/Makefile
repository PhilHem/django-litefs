# Makefile - CI contract for py-leader package
# All CI commands should go through make targets

.PHONY: lint lint-fix test test-unit test-property typecheck check

# Linting
lint:
	uv run ruff check .

lint-fix:
	uv run ruff check . --fix

# Testing
test:
	uv run pytest

test-unit:
	uv run pytest -m "tier(1)"

test-property:
	uv run pytest -m property

# Type checking
typecheck:
	uv run mypy src/py_leader/

# All checks (for CI)
check: lint typecheck test

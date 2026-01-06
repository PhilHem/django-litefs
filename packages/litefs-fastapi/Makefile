# Makefile - CI contract for litefs-fastapi package
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
	uv run mypy src/litefs_fastapi/

# All checks (for CI)
check: lint typecheck test

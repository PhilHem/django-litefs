# Makefile - CI contract for litefs-py package
# All CI commands should go through make targets

.PHONY: lint lint-fix test test-unit test-marker test-property typecheck check

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

test-marker:
	uv run pytest ../../tests/core/unit/usecases/test_primary_marker_writer.py -v

test-property:
	uv run pytest -m property

# Type checking
typecheck:
	uv run mypy src/litefs/

# All checks (for CI)
check: lint typecheck test

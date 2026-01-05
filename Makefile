# Makefile - CI contract for django-litefs
# All CI commands should go through make targets

.PHONY: lint lint-fix test test-unit test-integration test-property

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

test-integration:
	uv run pytest -m integration

test-property:
	uv run pytest -m property

# Type checking
typecheck:
	uv run mypy packages/litefs/src/litefs/ packages/litefs-django/src/litefs_django/

# All checks (for CI)
check: lint typecheck test

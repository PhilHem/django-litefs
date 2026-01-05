# Makefile - CI contract for litefs-django package
# All CI commands should go through make targets

.PHONY: lint lint-fix test test-unit test-apps test-property typecheck check

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

test-apps:
	uv run pytest ../../tests/django_adapter/unit/test_apps.py -v

test-property:
	uv run pytest -m property

# Type checking
typecheck:
	uv run mypy src/litefs_django/

# All checks (for CI)
check: lint typecheck test

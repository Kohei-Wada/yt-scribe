.PHONY: help install test lint format typecheck check hooks clean

.DEFAULT_GOAL := help

help: ## Show this help
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Create the dev environment
	uv sync --dev

hooks: ## Install the pre-commit hooks
	uv run pre-commit install --install-hooks
	uv run pre-commit install --hook-type commit-msg

test: ## Run the test suite
	uv run pytest -q

lint: ## Lint and check formatting
	uv run ruff check .
	uv run ruff format --check .

format: ## Fix what can be fixed automatically
	uv run ruff check --fix .
	uv run ruff format .

typecheck: ## Type-check the package
	uv run mypy yt_scribe

check: lint typecheck test ## Everything CI runs

clean: ## Remove caches and build output
	rm -rf .pytest_cache .ruff_cache .mypy_cache dist
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

.PHONY: install dev test lint format docker-up docker-down migrate seed eval serve clean help

# ── Variables ────────────────────────────────────────────────────────────────
PYTHON      := python
PIP         := pip
UVICORN     := uvicorn
ALEMBIC     := alembic
PYTEST      := pytest
RUFF        := ruff
MYPY        := mypy
DOCKER      := docker compose

SRC_DIR     := src
TEST_DIR    := tests
APP_MODULE  := src.api.main:app
HOST        := 0.0.0.0
PORT        := 8000

# ── Targets ──────────────────────────────────────────────────────────────────

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install base dependencies
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements/base.txt
	$(PIP) install -e .

dev: ## Install all dependencies (base + dev + ml)
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements/dev.txt
	$(PIP) install -e ".[dev]"
	pre-commit install

test: ## Run test suite with coverage
	$(PYTEST) $(TEST_DIR) \
		--cov=$(SRC_DIR) \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-fail-under=80 \
		-x

lint: ## Run linters (ruff + mypy)
	$(RUFF) check $(SRC_DIR) $(TEST_DIR)
	$(MYPY) $(SRC_DIR)

format: ## Auto-format code with ruff
	$(RUFF) check --fix $(SRC_DIR) $(TEST_DIR)
	$(RUFF) format $(SRC_DIR) $(TEST_DIR)

docker-up: ## Start all services via Docker Compose
	$(DOCKER) up -d --build
	@echo "Services started. API at http://localhost:$(PORT)/docs"

docker-down: ## Stop all Docker Compose services
	$(DOCKER) down -v --remove-orphans

migrate: ## Run database migrations (Alembic)
	$(ALEMBIC) upgrade head

migrate-new: ## Create a new migration (usage: make migrate-new MSG="add users table")
	$(ALEMBIC) revision --autogenerate -m "$(MSG)"

migrate-down: ## Rollback last migration
	$(ALEMBIC) downgrade -1

seed: ## Seed database with sample data
	$(PYTHON) -m src.db.seed

eval: ## Run LLM evaluation suite
	$(PYTHON) -m src.evaluation.run_eval

serve: ## Start the development server with hot reload
	$(UVICORN) $(APP_MODULE) \
		--host $(HOST) \
		--port $(PORT) \
		--reload \
		--reload-dir $(SRC_DIR) \
		--log-level info

serve-prod: ## Start the production server
	$(UVICORN) $(APP_MODULE) \
		--host $(HOST) \
		--port $(PORT) \
		--workers 4 \
		--log-level warning

clean: ## Remove build artifacts, caches, and temp files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist build htmlcov .coverage
	@echo "Cleaned."

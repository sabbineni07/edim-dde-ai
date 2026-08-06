# EDIM DDE AI — recommended developer commands
# Usage: make <target>

.PHONY: help install install-dev install-req install-req-dev test validate register register-dir list run demo build wheel release dist publish clean clean-dist lint-imports version cli-help

PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
PACKAGE := edim-dde-ai
EXAMPLE_YAML := examples/agents/echo_agent.agent.yaml
EXAMPLE_DIR := examples/agents
AGENT_ID ?= echo_agent
INPUT ?= {"message":"hi"}

help: ## Show this help
	@echo "$(PACKAGE) — make targets"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-16s %s\n", $$1, $$2}'
	@echo ""
	@echo "Variables: PYTHON=$(PYTHON) AGENT_ID=$(AGENT_ID)"
	@echo "Publish: set TWINE_REPOSITORY_URL + TWINE_USERNAME/TWINE_PASSWORD (see docs/PUBLISHING.md)"

install: ## Install package (editable) from pyproject
	$(PIP) install -e .

install-dev: ## Install package + dev deps (pytest, build)
	$(PIP) install -e ".[dev]"

install-req: ## Install runtime deps from requirements.txt only
	$(PIP) install -r requirements.txt

install-req-dev: ## Install runtime + dev deps from requirements-dev.txt
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -e .

test: ## Run pytest
	$(PYTHON) -m pytest -q

validate: ## Validate example agent YAML (structural CLI)
	$(PACKAGE) validate $(EXAMPLE_YAML)

validate-schema: ## BL-002: JSON Schema + extended blocks for examples (pytest)
	$(PYTHON) -m pytest -q tests/test_example_agent_schema.py

register: ## Register example agent YAML into CLI store
	$(PACKAGE) register $(EXAMPLE_YAML)

register-dir: ## Register all *.agent.yaml under examples/agents
	$(PACKAGE) register-dir $(EXAMPLE_DIR)

list: ## List registered agents (CLI store)
	$(PACKAGE) list

run: ## Run AGENT_ID with INPUT JSON (defaults: echo_agent)
	$(PACKAGE) run $(AGENT_ID) --input '$(INPUT)'

demo: validate register run ## Validate, register, and run the echo example

build: ## Build wheel into dist/ (legacy; prefer release)
	$(PYTHON) -m build --wheel
	@ls -la dist/*.whl

wheel: build ## Alias for build

release: ## Clean + build wheel and sdist into dist/
	./scripts/build_wheel.sh

dist: release ## Alias for release

publish: ## Upload dist/ with twine (needs TWINE_* or --repository; see docs/PUBLISHING.md)
	./scripts/publish.sh

clean-dist: ## Remove dist/ and build artifacts
	rm -rf dist/ build/ *.egg-info src/*.egg-info

clean: clean-dist ## Remove build artifacts and caches
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

version: ## Print package version via CLI
	$(PACKAGE) version

cli-help: ## Show CLI help
	$(PACKAGE) --help

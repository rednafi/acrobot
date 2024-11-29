path := .

.PHONY: init
init: ## Initialize the project.
	@echo
	@echo "Initializing the project..."
	@echo "============================"
	@echo
	@uv sync

.PHONY: run-local
run-local: ## Run the application locally.
	@echo
	@echo "Running the application locally..."
	@echo "=================================="
	@echo
	@uv run python -m src.main


.PHONY: lint
lint: ruff mypy	## Apply all the linters.

.PHONY: lint-check
lint-check:  ## Check whether the codebase satisfies the linter rules.
	@echo
	@echo "Checking linter rules..."
	@echo "========================"
	@echo
	@uv run ruff check $(path)
	@uv run mypy $(path)

.PHONY: ruff
ruff: ## Apply ruff.
	@echo "Applying ruff..."
	@echo "================"
	@echo
	@uv run ruff format $(path)
	@uv run ruff check --fix $(path)

.PHONY: mypy
mypy: ## Apply mypy.
	@echo
	@echo "Applying mypy..."
	@echo "================="
	@echo
	@uv run mypy $(path)

.PHONY: help
help: ## Show this help message.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: test
test: ## Run the tests against the current version of Python.
	export ENVIRONMENT=local && uv run pytest -vv && cd ..

.PHONY: deploy
deploy: ## Deploy the application to fly.io.
	@echo
	@echo "Deploying the application..."
	@echo "============================="
	@echo
	@fly deploy

.PHONY: destroy-machines
destroy-machines: ## Remove all the machines for this application.
	@echo
	@echo "Removing all the machines..."
	@echo "============================="
	@echo
	@fly machines destroy --force

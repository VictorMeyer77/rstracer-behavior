.ONESHELL:
ENV_PREFIX=$(shell python -c "if __import__('pathlib').Path('.venv/bin/pip').exists(): print('.venv/bin/')")

.PHONY: help
help:             ## Show the help.
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@fgrep "##" Makefile | fgrep -v fgrep


.PHONY: show
show:             ## Show the current environment.
	@echo "Current environment:"
	@echo "Running using $(ENV_PREFIX)"
	@$(ENV_PREFIX)python -V
	@$(ENV_PREFIX)python -m site

.PHONY: install
install:          ## Install the project in dev mode.
	@echo "Don't forget to run 'make virtualenv' if you got errors."
	$(ENV_PREFIX)pip install -e .[test]

.PHONY: fmt
fmt:              ## Format code using black & isort.
	$(ENV_PREFIX)isort pages/ rsbv.py setup.py rstracer.py
	$(ENV_PREFIX)black -l 120 pages/ rsbv.py setup.py rstracer.py

.PHONY: lint
lint:             ## Run flake8, black, mypy linters.
	$(ENV_PREFIX)flake8 --max-line-length 120 pages/ rsbv.py setup.py rstracer.py
	$(ENV_PREFIX)black -l 120 --check pages/ rsbv.py setup.py rstracer.py
	$(ENV_PREFIX)mypy --ignore-missing-imports pages/ rsbv.py setup.py rstracer.py

.PHONY: clean
clean:            ## Clean unused files.
	@rm -rf .cache
	@rm -rf .pytest_cache
	@rm -rf .mypy_cache
	@rm -rf build
	@rm -rf dist
	@rm -rf *.egg-info
	@rm -rf htmlcov
	@rm -rf .tox/
	@rm -rf docs/_build
	@rm -rf *.log
	@rm -rf *.db
	@rm -rf *.wal

.PHONY: virtualenv
virtualenv:       ## Create a virtual environment.
	@echo "creating virtualenv ..."
	@rm -rf .venv
	@python3 -m venv .venv
	@./.venv/bin/pip install -U pip
	@./.venv/bin/pip install -e .[test]
	@echo
	@echo "!!! Please run 'source .venv/bin/activate' to enable the environment !!!"

.PHONY: docs
docs:             ## Build the documentation.
	@echo "building documentation ..."
	@$(ENV_PREFIX)mkdocs build
	@$(ENV_PREFIX)mkdocs serve
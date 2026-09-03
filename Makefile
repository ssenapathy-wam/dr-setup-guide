.PHONY: help install install-dev test test-cov lint format clean clean-all setup-env run-dry-run docs

# ============================================================================
# Default Help
# ============================================================================
help:
	@echo "DR Setup Guide - Available Commands"
	@echo "===================================="
	@echo ""
	@echo "Setup Commands:"
	@echo "  make install          Install package with dependencies"
	@echo "  make install-dev      Install package with dev dependencies"
	@echo "  make setup-env        Setup environment from .env.example"
	@echo ""
	@echo "Development Commands:"
	@echo "  make lint             Run linting checks (flake8, pylint)"
	@echo "  make format           Format code with black"
	@echo "  make test             Run tests"
	@echo "  make test-cov         Run tests with coverage report"
	@echo ""
	@echo "Execution Commands:"
	@echo "  make run-dry-run      Run setup in dry-run mode"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs             Build documentation"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean            Remove cache and build files"
	@echo "  make clean-all        Remove all generated files including venv"

# ============================================================================
# Setup and Installation
# ============================================================================
install:
	@echo "Installing DR Setup Guide..."
	pip install -e .

install-dev:
	@echo "Installing DR Setup Guide with development dependencies..."
	pip install -e ".[dev,docs]"

setup-env:
	@echo "Setting up environment file..."
	@if [ -f .env ]; then \
		echo ".env already exists. Please check configuration."; \
	else \
		cp .env.example .env; \
		echo ".env created from .env.example. Please update with your values."; \
	fi

venv:
	@echo "Creating virtual environment..."
	python3 -m venv venv
	@echo "Virtual environment created. Run 'source venv/bin/activate' to activate."

# ============================================================================
# Development Commands
# ============================================================================
lint:
	@echo "Running linting checks..."
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	pylint **/*.py --disable=all --enable=E,F || true
	mypy . --ignore-missing-imports || true

format:
	@echo "Formatting code with black..."
	black . --line-length=100
	@echo "Code formatting complete"

test:
	@echo "Running tests..."
	pytest -v

test-cov:
	@echo "Running tests with coverage..."
	pytest --cov=. --cov-report=html --cov-report=term-missing -v
	@echo "Coverage report generated in htmlcov/index.html"

# ============================================================================
# Execution Commands
# ============================================================================
run-dry-run:
	@echo "Running DR setup in dry-run mode..."
	DRY_RUN=true DRY_RUN_VERBOSE=true python dr_orchestrator.py

# ============================================================================
# Documentation
# ============================================================================
docs:
	@echo "Building documentation..."
	cd docs && make html
	@echo "Documentation built in docs/_build/html/index.html"

# ============================================================================
# Maintenance
# ============================================================================
clean:
	@echo "Cleaning up cache and build files..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.py[cod]' -delete
	find . -type f -name '.coverage*' -delete
	rm -rf .pytest_cache .mypy_cache .tox htmlcov dist build *.egg-info
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleanup complete"

clean-all: clean
	@echo "Removing virtual environment..."
	rm -rf venv/
	@echo "Full cleanup complete"

# ============================================================================
# Requirements verification
# ============================================================================
check-requirements:
	@echo "Checking requirements..."
	pip check
	@echo "All requirements are satisfied"

requirements-update:
	@echo "Updating requirements.txt..."
	pip freeze > requirements.txt
	@echo "requirements.txt updated"

# ============================================================================
# Docker (if applicable)
# ============================================================================
docker-build:
	@echo "Building Docker image..."
	docker build -t dr-setup-guide:latest .

docker-run:
	@echo "Running Docker container..."
	docker run -it --env-file .env dr-setup-guide:latest

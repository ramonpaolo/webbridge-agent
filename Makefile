# Makefile for webbridge-agent

.PHONY: help install install-dev test test-unit test-integration test-security test-e2e test-all lint format clean run docker-build docker-up docker-down

# Default target
help:
	@echo "webbridge-agent - Makefile commands"
	@echo ""
	@echo "Development:"
	@echo "  make install         Install dependencies"
	@echo "  make install-dev     Install development dependencies"
	@echo "  make test            Run all tests"
	@echo "  make test-unit       Run unit tests only"
	@echo "  make test-integration Run integration tests only"
	@echo "  make test-security   Run security tests only"
	@echo "  make test-e2e       Run E2E tests (requires server running)"
	@echo "  make lint            Run linter"
	@echo "  make format          Format code"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build    Build Docker image"
	@echo "  make docker-up       Start services with docker-compose"
	@echo "  make docker-down     Stop services"
	@echo ""
	@echo "Server:"
	@echo "  make run             Run development server"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt -r requirements-dev.txt
	playwright install chromium

# Testing
test: test-unit test-integration test-security

test-unit:
	pytest tests/unit/ -v --tb=short

test-integration:
	pytest tests/integration/ -v --tb=short

test-security:
	pytest tests/security/ -v --tb=short

test-e2e:
	@echo "Starting server on port 8081..."
	uvicorn src.main:app --port 8081 &
	@echo "Waiting for server..."
	sleep 3
	pytest tests/e2e/ -v --tb=short
	@pkill -f "uvicorn src.main:app --port 8081" || true

test-all:
	pytest tests/ -v --tb=short --cov=src --cov-report=term-missing

# Code Quality
lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

# Server
run:
	uvicorn src.main:app --reload --port 8080

# Docker
docker-build:
	docker build -t agent-webbridge .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

# Cleanup
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/

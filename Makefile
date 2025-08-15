# Archivist Local Development Makefile
# Replaces GitHub Actions with local tools

.PHONY: help security-scan test install clean

help:
	@echo "Available commands:"
	@echo "  security-scan  - Run all security checks locally"
	@echo "  test          - Run tests"
	@echo "  install       - Install dependencies"
	@echo "  clean         - Clean up generated files"
	@echo "  format        - Format code with Black"
	@echo "  lint          - Run linting checks"

security-scan:
	@echo "🔒 Running local security scan..."
	python3 scripts/local_security_scan.py

test:
	@echo "🧪 Running tests..."
	python3 -m pytest tests/ -v

install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt
	pip install safety bandit semgrep black flake8 pytest

clean:
	@echo "🧹 Cleaning up..."
	rm -f *.json
	rm -f *.log
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +

format:
	@echo "🎨 Formatting code..."
	python3 -m black core/ tests/ scripts/

lint:
	@echo "🔍 Running linting checks..."
	python3 -m flake8 core/ --max-line-length=88
	python3 -m black --check core/ tests/ scripts/

# Quick security check (just the essentials)
security-quick:
	@echo "⚡ Quick security check..."
	safety check
	bandit -r core -f txt 
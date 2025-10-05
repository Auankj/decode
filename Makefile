# Cookie-Licking Detector - Development and Deployment Automation

.PHONY: help dev prod test clean build deploy lint format security docs

# Default target
help:
	@echo "Available targets:"
	@echo "  dev      - Start development environment"
	@echo "  prod     - Start production environment"
	@echo "  test     - Run test suite"
	@echo "  lint     - Run code linting"
	@echo "  format   - Format code"
	@echo "  security - Run security checks"
	@echo "  build    - Build Docker images"
	@echo "  clean    - Clean up containers and volumes"
	@echo "  docs     - Generate documentation"
	@echo "  migrate  - Run database migrations"
	@echo "  seed     - Seed database with test data"

# Development environment
dev:
	@echo "Starting development environment..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

dev-detach:
	@echo "Starting development environment in background..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d

# Production environment
prod:
	@echo "Starting production environment..."
	docker-compose up --build -d
	@echo "Production environment started. Services available at:"
	@echo "  - App: http://localhost:8000"
	@echo "  - Flower: http://localhost:5555"

# Testing
test:
	@echo "Running test suite..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec app pytest -v --cov=app --cov-report=html

test-ci:
	@echo "Running CI tests..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec app pytest --cov=app --cov-report=xml --junit-xml=pytest.xml

# Code quality
lint:
	@echo "Running linting checks..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec app flake8 app/
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec app mypy app/
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec app pylint app/

format:
	@echo "Formatting code..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec app black app/
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec app isort app/

# Security checks
security:
	@echo "Running security checks..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec app bandit -r app/
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec app safety check

# Database operations
migrate:
	@echo "Running database migrations..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec app alembic upgrade head

migrate-create:
	@echo "Creating new migration..."
	@read -p "Migration message: " msg; \
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec app alembic revision --autogenerate -m "$$msg"

seed:
	@echo "Seeding database..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec app python -c "from app.db.seed import seed_database; seed_database()"

# Build and deployment
build:
	@echo "Building Docker images..."
	docker-compose build --no-cache

build-prod:
	@echo "Building production Docker image..."
	docker build -t cookie-licking-detector:latest .

# Deployment
deploy-staging:
	@echo "Deploying to staging..."
	# Add staging deployment commands here
	
deploy-production:
	@echo "Deploying to production..."
	# Add production deployment commands here

# Cleanup
clean:
	@echo "Cleaning up containers and volumes..."
	docker-compose down -v --remove-orphans
	docker system prune -f

clean-all:
	@echo "Cleaning up everything including images..."
	docker-compose down -v --remove-orphans
	docker system prune -af

# Documentation
docs:
	@echo "Generating documentation..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec app mkdocs build

docs-serve:
	@echo "Serving documentation..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec app mkdocs serve

# Monitoring and debugging
logs:
	@echo "Showing application logs..."
	docker-compose logs -f app

logs-celery:
	@echo "Showing Celery worker logs..."
	docker-compose logs -f celery-worker

monitor:
	@echo "Opening monitoring interfaces..."
	@echo "  - Flower (Celery): http://localhost:5555"
	@echo "  - pgAdmin: http://localhost:8080"
	@echo "  - Redis Commander: http://localhost:8081"

# Performance testing
load-test:
	@echo "Running load tests..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec app locust -f tests/load/locustfile.py --headless -u 10 -r 2 -t 30s --host=http://localhost:8000

# Quick commands for common tasks
shell:
	@echo "Opening application shell..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec app bash

db-shell:
	@echo "Opening database shell..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec db psql -U cookie_user -d cookie_detector_dev

redis-shell:
	@echo "Opening Redis shell..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec redis redis-cli

# Installation and setup
install-hooks:
	@echo "Installing pre-commit hooks..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec app pre-commit install
#!/bin/bash

# Cookie Licking Detector - Production Deployment Script
# This script handles production deployment with proper checks and rollbacks

set -euo pipefail

# Configuration
PROJECT_NAME="cookie-licking-detector"
DOCKER_IMAGE="${PROJECT_NAME}:latest"
BACKUP_DIR="/backups"
LOG_FILE="/var/log/${PROJECT_NAME}/deploy.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "${LOG_FILE}"
}

info() {
    log "INFO" "${GREEN}$*${NC}"
}

warn() {
    log "WARN" "${YELLOW}$*${NC}"
}

error() {
    log "ERROR" "${RED}$*${NC}"
}

# Check prerequisites
check_prerequisites() {
    info "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed"
        exit 1
    fi
    
    if [[ ! -f ".env" ]]; then
        error ".env file not found. Copy .env.example to .env and configure it"
        exit 1
    fi
    
    info "Prerequisites check passed"
}

# Create backup
create_backup() {
    info "Creating database backup..."
    
    mkdir -p "${BACKUP_DIR}"
    local backup_file="${BACKUP_DIR}/backup_$(date +%Y%m%d_%H%M%S).sql"
    
    docker-compose exec -T db pg_dump -U cookie_user -d cookie_detector_prod > "${backup_file}"
    
    if [[ $? -eq 0 ]]; then
        info "Backup created: ${backup_file}"
        # Compress backup
        gzip "${backup_file}"
        info "Backup compressed: ${backup_file}.gz"
    else
        error "Failed to create backup"
        exit 1
    fi
}

# Build and test image
build_image() {
    info "Building Docker image..."
    
    # Build the image
    docker build -t "${DOCKER_IMAGE}" .
    
    if [[ $? -ne 0 ]]; then
        error "Failed to build Docker image"
        exit 1
    fi
    
    info "Docker image built successfully"
}

# Run pre-deployment tests
run_tests() {
    info "Running pre-deployment tests..."
    
    # Start test environment
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d db redis
    sleep 10
    
    # Run tests
    docker run --rm \
        --network "${PROJECT_NAME}_default" \
        -e DATABASE_URL="postgresql://cookie_user:cookie_password@db:5432/cookie_detector_dev" \
        -e REDIS_URL="redis://redis:6379/0" \
        -e ENVIRONMENT="testing" \
        "${DOCKER_IMAGE}" pytest -v --tb=short
    
    local test_result=$?
    
    # Cleanup test environment
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
    
    if [[ ${test_result} -ne 0 ]]; then
        error "Tests failed"
        exit 1
    fi
    
    info "All tests passed"
}

# Deploy application
deploy() {
    info "Deploying application..."
    
    # Pull latest images
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml pull
    
    # Stop services gracefully
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml down --timeout 30
    
    # Start services
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
    
    info "Waiting for services to start..."
    sleep 30
    
    # Check if services are healthy
    if ! check_health; then
        error "Health check failed"
        rollback
        exit 1
    fi
    
    # Run database migrations
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec -T app alembic upgrade head
    
    info "Deployment completed successfully"
}

# Health check
check_health() {
    info "Running health checks..."
    
    local max_attempts=30
    local attempt=1
    
    while [[ ${attempt} -le ${max_attempts} ]]; do
        if curl -sf http://localhost:8000/health > /dev/null; then
            info "Health check passed"
            return 0
        fi
        
        warn "Health check attempt ${attempt}/${max_attempts} failed, retrying..."
        sleep 10
        ((attempt++))
    done
    
    error "Health check failed after ${max_attempts} attempts"
    return 1
}

# Rollback function
rollback() {
    warn "Rolling back deployment..."
    
    # Stop current deployment
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
    
    # Find the latest backup
    local latest_backup=$(ls -t "${BACKUP_DIR}"/*.sql.gz 2>/dev/null | head -1)
    
    if [[ -n "${latest_backup}" ]]; then
        warn "Restoring from backup: ${latest_backup}"
        
        # Start database
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d db
        sleep 10
        
        # Restore database
        gunzip -c "${latest_backup}" | docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db psql -U cookie_user -d cookie_detector_prod
        
        warn "Database restored from backup"
    else
        error "No backup found for rollback"
    fi
    
    # TODO: Implement application rollback to previous version
    warn "Manual intervention required for complete rollback"
}

# Cleanup old images and containers
cleanup() {
    info "Cleaning up old Docker images and containers..."
    
    # Remove dangling images
    docker image prune -f
    
    # Remove old backups (keep last 7 days)
    find "${BACKUP_DIR}" -name "*.sql.gz" -type f -mtime +7 -delete
    
    info "Cleanup completed"
}

# Main deployment flow
main() {
    local action="${1:-deploy}"
    
    case "${action}" in
        "deploy")
            info "Starting deployment process..."
            check_prerequisites
            create_backup
            build_image
            run_tests
            deploy
            cleanup
            info "Deployment completed successfully!"
            ;;
        "rollback")
            warn "Starting rollback process..."
            rollback
            ;;
        "health")
            check_health
            ;;
        "backup")
            create_backup
            ;;
        *)
            echo "Usage: $0 {deploy|rollback|health|backup}"
            echo "  deploy   - Full deployment process"
            echo "  rollback - Rollback to previous version"
            echo "  health   - Run health check"
            echo "  backup   - Create database backup"
            exit 1
            ;;
    esac
}

# Ensure log directory exists
mkdir -p "$(dirname "${LOG_FILE}")"

# Run main function with all arguments
main "$@"
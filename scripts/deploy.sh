#!/bin/bash
#
# Deployment script for Code Cobra
#
# Usage:
#   ./scripts/deploy.sh [environment]
#
# Environments:
#   dev     - Development (default)
#   stage   - Staging
#   prod    - Production
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-dev}"
DEPLOY_TAG="${DEPLOY_TAG:-$(date +%Y%m%d-%H%M%S)}"
IMAGE_NAME="code-cobra"
REGISTRY="${REGISTRY:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate environment
validate_environment() {
    case "$ENVIRONMENT" in
        dev|stage|prod)
            log_info "Deploying to: $ENVIRONMENT"
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT"
            log_error "Valid options: dev, stage, prod"
            exit 1
            ;;
    esac
}

# Pre-deployment checks
pre_deploy_checks() {
    log_info "Running pre-deployment checks..."

    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    # Check if config exists
    if [[ ! -f "$PROJECT_ROOT/config/${ENVIRONMENT}.json" ]]; then
        log_error "Config file not found: config/${ENVIRONMENT}.json"
        exit 1
    fi

    # Run tests
    log_info "Running tests..."
    cd "$PROJECT_ROOT"
    if ! python -m unittest discover -s tests -p 'test_*.py' -q 2>/dev/null; then
        log_error "Tests failed - aborting deployment"
        exit 1
    fi
    log_info "All tests passed"

    # Run security checks
    log_info "Running security checks..."
    if ! python scripts/backdoor_check.py "$PROJECT_ROOT" >/dev/null 2>&1; then
        log_error "Security checks failed - aborting deployment"
        exit 1
    fi
    log_info "Security checks passed"
}

# Build Docker image
build_image() {
    log_info "Building Docker image..."

    local tag="${IMAGE_NAME}:${DEPLOY_TAG}"
    local env_tag="${IMAGE_NAME}:${ENVIRONMENT}"

    cd "$PROJECT_ROOT"

    docker build \
        --build-arg BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --build-arg VERSION="${DEPLOY_TAG}" \
        --build-arg ENVIRONMENT="${ENVIRONMENT}" \
        -t "$tag" \
        -t "$env_tag" \
        -t "${IMAGE_NAME}:latest" \
        .

    log_info "Built image: $tag"

    # Push to registry if specified
    if [[ -n "$REGISTRY" ]]; then
        log_info "Pushing to registry: $REGISTRY"
        docker tag "$tag" "${REGISTRY}/${tag}"
        docker tag "$env_tag" "${REGISTRY}/${env_tag}"
        docker push "${REGISTRY}/${tag}"
        docker push "${REGISTRY}/${env_tag}"
        log_info "Pushed images to registry"
    fi
}

# Deploy to environment
deploy() {
    log_info "Deploying to $ENVIRONMENT..."

    local compose_file="docker-compose.yml"
    if [[ -f "$PROJECT_ROOT/docker-compose.${ENVIRONMENT}.yml" ]]; then
        compose_file="docker-compose.${ENVIRONMENT}.yml"
    fi

    cd "$PROJECT_ROOT"

    # Set environment variables
    export ENVIRONMENT
    export DEPLOY_TAG
    export CONFIG_FILE="config/${ENVIRONMENT}.json"

    case "$ENVIRONMENT" in
        dev)
            deploy_dev
            ;;
        stage)
            deploy_stage
            ;;
        prod)
            deploy_prod
            ;;
    esac
}

deploy_dev() {
    log_info "Starting development deployment..."

    docker compose -f docker-compose.yml down --remove-orphans 2>/dev/null || true
    docker compose -f docker-compose.yml up -d

    log_info "Development deployment complete"
    log_info "Access at: http://localhost:11434"
}

deploy_stage() {
    log_info "Starting staging deployment..."

    # Create staging network if not exists
    docker network create code-cobra-stage 2>/dev/null || true

    # Stop existing containers
    docker compose -f docker-compose.yml -p code-cobra-stage down 2>/dev/null || true

    # Deploy with staging config
    docker compose -f docker-compose.yml -p code-cobra-stage up -d

    log_info "Staging deployment complete"
}

deploy_prod() {
    log_info "Starting production deployment..."

    # Production requires confirmation
    if [[ "${FORCE:-}" != "true" ]]; then
        log_warn "Production deployment requires confirmation"
        read -p "Are you sure you want to deploy to production? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            log_info "Deployment cancelled"
            exit 0
        fi
    fi

    # Blue-green deployment for production
    local current_color=$(docker ps --filter "name=code-cobra-blue" --format "{{.Names}}" | head -1)
    local new_color="blue"
    if [[ -n "$current_color" ]]; then
        new_color="green"
    fi

    log_info "Deploying to $new_color environment..."

    # Deploy new version
    docker compose -f docker-compose.yml -p "code-cobra-${new_color}" up -d

    # Health check
    log_info "Waiting for health check..."
    sleep 10

    if docker compose -p "code-cobra-${new_color}" ps | grep -q "healthy\|running"; then
        log_info "New deployment is healthy"

        # Switch traffic (would integrate with load balancer in real setup)
        old_color=$([[ "$new_color" == "blue" ]] && echo "green" || echo "blue")
        docker compose -p "code-cobra-${old_color}" down 2>/dev/null || true

        log_info "Production deployment complete"
    else
        log_error "Health check failed - rolling back"
        docker compose -p "code-cobra-${new_color}" down
        exit 1
    fi
}

# Post-deployment verification
verify_deployment() {
    log_info "Verifying deployment..."

    # Check if containers are running
    if docker compose ps 2>/dev/null | grep -q "running\|Up"; then
        log_info "Containers are running"
    else
        log_warn "No containers detected via docker-compose"
    fi

    log_info "Deployment verification complete"
}

# Rollback function
rollback() {
    log_warn "Rolling back deployment..."

    local previous_tag="${ROLLBACK_TAG:-}"
    if [[ -z "$previous_tag" ]]; then
        log_error "No rollback tag specified. Set ROLLBACK_TAG environment variable."
        exit 1
    fi

    DEPLOY_TAG="$previous_tag"
    deploy

    log_info "Rollback complete"
}

# Cleanup old images
cleanup() {
    log_info "Cleaning up old images..."

    # Keep last 5 images
    docker images "${IMAGE_NAME}" --format "{{.Tag}}" | \
        sort -r | \
        tail -n +6 | \
        xargs -I {} docker rmi "${IMAGE_NAME}:{}" 2>/dev/null || true

    # Prune dangling images
    docker image prune -f

    log_info "Cleanup complete"
}

# Main
main() {
    log_info "=== Code Cobra Deployment ==="
    log_info "Environment: $ENVIRONMENT"
    log_info "Deploy Tag: $DEPLOY_TAG"
    log_info "========================="

    validate_environment
    pre_deploy_checks
    build_image
    deploy
    verify_deployment

    log_info "=== Deployment Complete ==="
}

# Handle commands
case "${1:-}" in
    rollback)
        rollback
        ;;
    cleanup)
        cleanup
        ;;
    *)
        main
        ;;
esac

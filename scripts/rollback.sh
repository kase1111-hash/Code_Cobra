#!/bin/bash
#
# Rollback and recovery script for Code Cobra
#
# Usage:
#   ./scripts/rollback.sh [command] [options]
#
# Commands:
#   list        - List available rollback points
#   rollback    - Rollback to a specific version
#   recover     - Recover from a failed state
#   backup      - Create a backup point
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/.backups}"
MAX_BACKUPS="${MAX_BACKUPS:-10}"
IMAGE_NAME="code-cobra"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_debug() { echo -e "${BLUE}[DEBUG]${NC} $1"; }

# Ensure backup directory exists
ensure_backup_dir() {
    mkdir -p "$BACKUP_DIR"
}

# List available rollback points
list_rollback_points() {
    log_info "Available rollback points:"
    echo ""

    # Git tags
    echo "=== Git Tags ==="
    git -C "$PROJECT_ROOT" tag -l --sort=-creatordate | head -10 | while read -r tag; do
        date=$(git -C "$PROJECT_ROOT" log -1 --format="%ci" "$tag" 2>/dev/null || echo "unknown")
        echo "  $tag ($date)"
    done

    echo ""

    # Docker images
    echo "=== Docker Images ==="
    docker images "$IMAGE_NAME" --format "  {{.Tag}}\t{{.CreatedAt}}" 2>/dev/null | head -10 || echo "  No images found"

    echo ""

    # Backup files
    echo "=== Backup Files ==="
    if [[ -d "$BACKUP_DIR" ]]; then
        ls -lt "$BACKUP_DIR"/*.tar.gz 2>/dev/null | head -10 | awk '{print "  " $NF " (" $6 " " $7 " " $8 ")"}' || echo "  No backups found"
    else
        echo "  No backups found"
    fi
}

# Create a backup
create_backup() {
    local name="${1:-$(date +%Y%m%d-%H%M%S)}"
    ensure_backup_dir

    log_info "Creating backup: $name"

    local backup_file="$BACKUP_DIR/backup-$name.tar.gz"

    # Create tarball of important files
    cd "$PROJECT_ROOT"
    tar -czf "$backup_file" \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.backups' \
        --exclude='venv' \
        --exclude='node_modules' \
        . 2>/dev/null

    log_info "Backup created: $backup_file"

    # Record Docker image if running
    if docker ps --filter "ancestor=$IMAGE_NAME" --format "{{.Image}}" | head -1 > /dev/null 2>&1; then
        docker ps --filter "ancestor=$IMAGE_NAME" --format "{{.Image}}" | head -1 > "$BACKUP_DIR/backup-$name.docker"
        log_info "Docker image recorded"
    fi

    # Cleanup old backups
    cleanup_old_backups
}

# Cleanup old backups
cleanup_old_backups() {
    local count
    count=$(ls -1 "$BACKUP_DIR"/*.tar.gz 2>/dev/null | wc -l)

    if [[ "$count" -gt "$MAX_BACKUPS" ]]; then
        log_info "Cleaning up old backups (keeping $MAX_BACKUPS)"
        ls -t "$BACKUP_DIR"/*.tar.gz | tail -n +$((MAX_BACKUPS + 1)) | xargs rm -f
    fi
}

# Rollback to a specific point
rollback() {
    local target="${1:-}"

    if [[ -z "$target" ]]; then
        log_error "Please specify a rollback target"
        log_info "Usage: rollback.sh rollback <git-tag|docker-tag|backup-file>"
        exit 1
    fi

    # Create backup before rollback
    log_info "Creating pre-rollback backup..."
    create_backup "pre-rollback-$(date +%Y%m%d-%H%M%S)"

    # Determine rollback type
    if git -C "$PROJECT_ROOT" rev-parse "$target" >/dev/null 2>&1; then
        rollback_git "$target"
    elif docker image inspect "$IMAGE_NAME:$target" >/dev/null 2>&1; then
        rollback_docker "$target"
    elif [[ -f "$BACKUP_DIR/backup-$target.tar.gz" ]]; then
        rollback_backup "$target"
    elif [[ -f "$target" ]]; then
        rollback_backup_file "$target"
    else
        log_error "Rollback target not found: $target"
        exit 1
    fi
}

# Rollback using Git
rollback_git() {
    local tag="$1"
    log_info "Rolling back to git tag: $tag"

    cd "$PROJECT_ROOT"

    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD --; then
        log_warn "Uncommitted changes detected. Stashing..."
        git stash push -m "Pre-rollback stash $(date +%Y%m%d-%H%M%S)"
    fi

    # Checkout the tag
    git checkout "$tag"

    log_info "Git rollback complete"
    log_info "Note: You are now in detached HEAD state"
}

# Rollback using Docker
rollback_docker() {
    local tag="$1"
    log_info "Rolling back to Docker image: $IMAGE_NAME:$tag"

    # Stop current containers
    docker compose -f "$PROJECT_ROOT/docker-compose.yml" down 2>/dev/null || true

    # Update compose to use specific image
    export IMAGE_TAG="$tag"

    # Start with rollback image
    docker compose -f "$PROJECT_ROOT/docker-compose.yml" up -d

    log_info "Docker rollback complete"
}

# Rollback from backup file
rollback_backup() {
    local name="$1"
    rollback_backup_file "$BACKUP_DIR/backup-$name.tar.gz"
}

rollback_backup_file() {
    local backup_file="$1"

    if [[ ! -f "$backup_file" ]]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi

    log_info "Rolling back from backup: $backup_file"

    # Stop any running services
    docker compose -f "$PROJECT_ROOT/docker-compose.yml" down 2>/dev/null || true

    # Extract backup
    cd "$PROJECT_ROOT"
    tar -xzf "$backup_file"

    # Restart services
    docker compose -f "$PROJECT_ROOT/docker-compose.yml" up -d 2>/dev/null || true

    log_info "Backup rollback complete"
}

# Recover from failed state
recover() {
    log_info "Starting recovery process..."

    # Step 1: Check Docker status
    log_info "Step 1: Checking Docker status..."
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    log_info "Docker is running"

    # Step 2: Stop all Code Cobra containers
    log_info "Step 2: Stopping all Code Cobra containers..."
    docker ps -a --filter "name=code-cobra" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
    log_info "Containers stopped"

    # Step 3: Clean up networks
    log_info "Step 3: Cleaning up networks..."
    docker network prune -f 2>/dev/null || true

    # Step 4: Check for corrupted files
    log_info "Step 4: Checking for corrupted files..."
    cd "$PROJECT_ROOT"

    # Verify Python files
    python_errors=0
    for pyfile in *.py; do
        if [[ -f "$pyfile" ]] && ! python -m py_compile "$pyfile" 2>/dev/null; then
            log_warn "Syntax error in: $pyfile"
            ((python_errors++))
        fi
    done

    if [[ "$python_errors" -gt 0 ]]; then
        log_warn "Found $python_errors Python files with errors"
        log_info "Consider rolling back to a known good state"
    else
        log_info "All Python files OK"
    fi

    # Step 5: Verify configuration
    log_info "Step 5: Verifying configuration..."
    for config in config/*.json; do
        if [[ -f "$config" ]] && ! python -c "import json; json.load(open('$config'))" 2>/dev/null; then
            log_warn "Invalid JSON: $config"
        fi
    done
    log_info "Configuration check complete"

    # Step 6: Attempt restart
    log_info "Step 6: Attempting to restart services..."
    if docker compose -f "$PROJECT_ROOT/docker-compose.yml" up -d 2>/dev/null; then
        log_info "Services restarted successfully"
    else
        log_warn "Could not restart services automatically"
        log_info "You may need to run: docker compose up -d"
    fi

    log_info "Recovery process complete"
}

# Health check
check_health() {
    log_info "Running health check..."

    # Check if Python works
    if python --version >/dev/null 2>&1; then
        log_info "Python: OK"
    else
        log_error "Python: FAILED"
    fi

    # Check main application
    if python -c "import autonomous_ensemble" 2>/dev/null; then
        log_info "Application import: OK"
    else
        log_error "Application import: FAILED"
    fi

    # Check Docker
    if docker info >/dev/null 2>&1; then
        log_info "Docker: OK"
    else
        log_warn "Docker: NOT RUNNING"
    fi

    # Check containers
    running=$(docker ps --filter "name=code-cobra" --format "{{.Names}}" | wc -l)
    log_info "Running containers: $running"
}

# Show help
show_help() {
    cat << EOF
Code Cobra Rollback and Recovery Tool

Usage: $0 <command> [options]

Commands:
  list              List available rollback points
  backup [name]     Create a backup (optional name)
  rollback <target> Rollback to a specific version
                    Target can be: git tag, docker tag, or backup name
  recover           Attempt to recover from a failed state
  health            Run health checks

Examples:
  $0 list
  $0 backup before-update
  $0 rollback v1.0.0
  $0 rollback 20240115-120000
  $0 recover
  $0 health

Environment Variables:
  BACKUP_DIR   Directory for backups (default: .backups)
  MAX_BACKUPS  Maximum number of backups to keep (default: 10)

EOF
}

# Main
main() {
    local command="${1:-help}"
    shift || true

    case "$command" in
        list)
            list_rollback_points
            ;;
        backup)
            create_backup "$@"
            ;;
        rollback)
            rollback "$@"
            ;;
        recover)
            recover
            ;;
        health)
            check_health
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

main "$@"

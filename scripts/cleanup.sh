#!/bin/bash

###############################################################################
# Cleanup Script - Remove temporary files and caches
###############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

echo "========================================"
echo "🧹 SecurePay Wallet Cleanup"
echo "========================================"
echo ""

# Get project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

log_info "Project root: $PROJECT_ROOT"
echo ""

###############################################################################
# Python Cache Cleanup
###############################################################################

log_info "Cleaning Python cache files..."

# Remove __pycache__ directories
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Remove .pyc files
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Remove .pyo files
find . -type f -name "*.pyo" -delete 2>/dev/null || true

# Remove .pyd files (Windows)
find . -type f -name "*.pyd" -delete 2>/dev/null || true

log_success "Python cache cleaned"

###############################################################################
# Test Cache Cleanup
###############################################################################

log_info "Cleaning test cache..."

# Remove pytest cache
rm -rf .pytest_cache 2>/dev/null || true

# Remove coverage files
rm -f .coverage 2>/dev/null || true
rm -rf htmlcov/ 2>/dev/null || true
rm -f coverage.xml 2>/dev/null || true

log_success "Test cache cleaned"

###############################################################################
# Build Artifacts Cleanup
###############################################################################

log_info "Cleaning build artifacts..."

# Remove dist directories
rm -rf dist/ 2>/dev/null || true
rm -rf build/ 2>/dev/null || true

# Remove egg-info
rm -rf *.egg-info 2>/dev/null || true

log_success "Build artifacts cleaned"

###############################################################################
# Log File Cleanup
###############################################################################

log_info "Cleaning log files..."

# Remove uvicorn logs
rm -f uvicorn.log 2>/dev/null || true

# Remove application logs
rm -f app.log 2>/dev/null || true
rm -f error.log 2>/dev/null || true

log_success "Log files cleaned"

###############################################################################
# IDE Cache Cleanup
###############################################################################

log_info "Cleaning IDE cache files..."

# VS Code
rm -rf .vscode/__pycache__ 2>/dev/null || true

# PyCharm
rm -rf .idea/__pycache__ 2>/dev/null || true

# Jupyter
find . -type d -name ".ipynb_checkpoints" -exec rm -rf {} + 2>/dev/null || true

log_success "IDE cache cleaned"

###############################################################################
# Database Cleanup (Optional)
###############################################################################

if [ "$1" == "--db" ]; then
    log_warning "Database cleanup requested..."
    
    # Remove SQLite databases (if any)
    rm -f *.db 2>/dev/null || true
    rm -f *.sqlite 2>/dev/null || true
    rm -f *.sqlite3 2>/dev/null || true
    
    log_success "Database files cleaned"
fi

###############################################################################
# Virtual Environment Cleanup (Optional - DANGEROUS)
###############################################################################

if [ "$1" == "--venv" ]; then
    log_warning "Virtual environment cleanup requested..."
    log_warning "This will delete the entire .venv directory!"
    
    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" == "yes" ]; then
        rm -rf .venv/ 2>/dev/null || true
        rm -rf venv/ 2>/dev/null || true
        log_success "Virtual environment removed"
        log_info "Recreate with: python -m venv .venv && source .venv/bin/activate && uv pip install -r requirements.txt"
    else
        log_info "Skipped virtual environment cleanup"
    fi
fi

###############################################################################
# Summary
###############################################################################

echo ""
echo "========================================"
log_success "Cleanup completed!"
echo "========================================"
echo ""

log_info "Usage:"
echo "  bash scripts/cleanup.sh           # Standard cleanup"
echo "  bash scripts/cleanup.sh --db      # Include database files"
echo "  bash scripts/cleanup.sh --venv    # Remove virtual environment (requires confirmation)"
echo ""

# Show disk space saved (if du is available)
if command -v du &> /dev/null; then
    cache_size=$(du -sh . 2>/dev/null | cut -f1)
    log_info "Current project size: $cache_size"
fi

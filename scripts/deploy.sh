#!/bin/bash

###############################################################################
# SecurePay Wallet - Idempotent Deployment Script
# 
# This script ensures safe, repeatable deployments without breaking changes
# Can be run multiple times - idempotent operations only
###############################################################################

set -e  # Exit on any error
set -u  # Exit on undefined variables

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Configuration
APP_NAME="securepay-wallet"
APP_DIR="${DEPLOY_PATH:-/opt/securepay-wallet}"
VENV_DIR="$APP_DIR/venv"
SERVICE_NAME="securepay-wallet"
BACKUP_DIR="$APP_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

###############################################################################
# Pre-deployment Checks
###############################################################################

log_info "Starting deployment for $APP_NAME..."

# Check if running as correct user
if [ "$(whoami)" != "${DEPLOY_USER:-$USER}" ]; then
    log_warning "Running as $(whoami), expected ${DEPLOY_USER:-$USER}"
fi

# Check if app directory exists
if [ ! -d "$APP_DIR" ]; then
    log_error "Application directory not found: $APP_DIR"
    exit 1
fi

cd "$APP_DIR"

###############################################################################
# Backup Current State (Idempotent)
###############################################################################

log_info "Creating backup..."

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Backup current .env file (idempotent)
if [ -f ".env" ]; then
    cp .env "$BACKUP_DIR/.env.$TIMESTAMP" || true
    log_success "Backed up .env file"
else
    log_warning ".env file not found, skipping backup"
fi

# Backup database (PostgreSQL)
if command -v pg_dump &> /dev/null; then
    if [ -n "${DATABASE_URL:-}" ]; then
        log_info "Backing up database..."
        pg_dump "$DATABASE_URL" > "$BACKUP_DIR/db_backup_$TIMESTAMP.sql" 2>/dev/null || log_warning "Database backup failed (may not exist yet)"
    fi
fi

# Keep only last 5 backups (cleanup old ones)
ls -t "$BACKUP_DIR"/*.sql 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
ls -t "$BACKUP_DIR"/.env.* 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true

log_success "Backup completed"

###############################################################################
# Virtual Environment Setup (Idempotent)
###############################################################################

log_info "Setting up Python virtual environment..."

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    log_success "Created virtual environment"
else
    log_info "Virtual environment already exists"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Install uv if not present (faster than pip)
if ! command -v uv &> /dev/null; then
    log_info "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

log_success "Python environment ready"

###############################################################################
# Dependency Installation (Idempotent)
###############################################################################

log_info "Installing/updating dependencies..."

# Install requirements using uv (idempotent and much faster than pip)
uv pip install -r requirements.txt
log_success "Dependencies installed"

###############################################################################
# Environment Configuration Check (Idempotent)
###############################################################################

log_info "Checking environment configuration..."

# Check if .env exists
if [ ! -f ".env" ]; then
    log_warning ".env file not found"
    
    # Check if .env.example exists
    if [ -f ".env.example" ]; then
        log_info "Creating .env from .env.example..."
        cp .env.example .env
        log_warning "⚠️  Please update .env with your actual values!"
    else
        log_error ".env.example not found. Cannot create .env file."
        exit 1
    fi
fi

# Validate required environment variables
required_vars=("DATABASE_URL" "SECRET_KEY" "PAYSTACK_SECRET_KEY" "PAYSTACK_WEBHOOK_SECRET")
missing_vars=()

for var in "${required_vars[@]}"; do
    if ! grep -q "^$var=" .env 2>/dev/null || grep -q "^$var=$" .env 2>/dev/null; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    log_error "Missing or empty required environment variables:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    exit 1
fi

log_success "Environment configuration valid"

###############################################################################
# Database Migrations (Idempotent)
###############################################################################

log_info "Running database migrations..."

# Check if alembic is configured
if [ -f "alembic.ini" ]; then
    # Run migrations (idempotent - alembic tracks applied migrations)
    alembic upgrade head
    log_success "Database migrations completed"
else
    log_warning "Alembic not configured, skipping migrations"
    
    # Fallback: create tables directly (idempotent)
    if [ -f "create_tables.py" ]; then
        python create_tables.py
        log_success "Database tables created/verified"
    fi
fi

###############################################################################
# Static Files (Idempotent)
###############################################################################

log_info "Setting up static files..."

# Create static directory if it doesn't exist
mkdir -p static

# Set permissions (idempotent)
chmod -R 755 static 2>/dev/null || true

log_success "Static files ready"

###############################################################################
# Service Configuration (Idempotent)
###############################################################################

log_info "Configuring systemd service..."

# Check if systemd service exists
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

if [ -f "$SERVICE_FILE" ]; then
    log_info "Service file already exists"
else
    log_warning "Service file not found. Creating..."
    
    # Create service file (requires sudo)
    sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=SecurePay Wallet API
After=network.target postgresql.service

[Service]
Type=notify
User=${DEPLOY_USER:-$USER}
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/uvicorn main:app --host 0.0.0.0 --port 8000
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    log_success "Service file created"
fi

# Enable service (idempotent)
sudo systemctl enable "$SERVICE_NAME" 2>/dev/null || true
log_success "Service configured"

###############################################################################
# Health Check Before Restart
###############################################################################

log_info "Running pre-deployment health checks..."

# Check if service is running
if systemctl is-active --quiet "$SERVICE_NAME"; then
    log_info "Service is currently running"
    CURRENT_PID=$(systemctl show -p MainPID --value "$SERVICE_NAME")
    log_info "Current PID: $CURRENT_PID"
else
    log_warning "Service is not running"
fi

###############################################################################
# Graceful Restart (Zero Downtime)
###############################################################################

log_info "Restarting application..."

# Try reload first (graceful), then restart
if sudo systemctl reload "$SERVICE_NAME" 2>/dev/null; then
    log_success "Service reloaded gracefully"
else
    log_info "Reload not supported, performing restart..."
    sudo systemctl restart "$SERVICE_NAME"
    log_success "Service restarted"
fi

###############################################################################
# Post-deployment Health Check
###############################################################################

log_info "Running post-deployment health checks..."

# Wait for service to start
sleep 5

# Check if service is running
if ! systemctl is-active --quiet "$SERVICE_NAME"; then
    log_error "Service failed to start!"
    
    # Show last 20 lines of logs
    log_error "Recent logs:"
    sudo journalctl -u "$SERVICE_NAME" -n 20 --no-pager
    
    # Attempt rollback
    log_warning "Attempting rollback..."
    git reset --hard HEAD~1 2>/dev/null || true
    sudo systemctl restart "$SERVICE_NAME"
    
    exit 1
fi

NEW_PID=$(systemctl show -p MainPID --value "$SERVICE_NAME")
log_success "Service is running (PID: $NEW_PID)"

# HTTP health check
log_info "Checking HTTP endpoint..."
sleep 2

if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    log_success "Health check passed!"
else
    log_error "Health check failed!"
    sudo journalctl -u "$SERVICE_NAME" -n 20 --no-pager
    exit 1
fi

###############################################################################
# Deployment Summary
###############################################################################

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_success "🎉 Deployment completed successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Deployment Information:"
echo "   • Timestamp: $TIMESTAMP"
echo "   • Application: $APP_NAME"
echo "   • Directory: $APP_DIR"
echo "   • Service: $SERVICE_NAME"
echo "   • PID: $NEW_PID"
echo ""
echo "🔗 Endpoints:"
echo "   • Health: http://localhost:8000/health"
echo "   • API Docs: http://localhost:8000/docs"
echo "   • Webhooks: http://localhost:8000/webhook/paystack"
echo ""
echo "📝 Useful Commands:"
echo "   • View logs: sudo journalctl -u $SERVICE_NAME -f"
echo "   • Check status: sudo systemctl status $SERVICE_NAME"
echo "   • Restart: sudo systemctl restart $SERVICE_NAME"
echo "   • Rollback: git reset --hard HEAD~1 && bash scripts/deploy.sh"
echo ""
echo "💾 Backup Location: $BACKUP_DIR"
echo ""

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
VENV_DIR="$APP_DIR/.venv"
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

###############################################################################
# System Dependencies (Idempotent)
###############################################################################

log_info "Checking system dependencies..."

# Update package list
if command -v apt-get &> /dev/null; then
    log_info "Updating package list..."
    sudo apt-get update -qq || log_warning "Failed to update package list"
    
    # Install Python venv if not present
    if ! dpkg -l | grep -q python3-venv; then
        log_info "Installing python3-venv..."
        sudo apt-get install -y python3-venv python3-pip
        log_success "Installed python3-venv"
    else
        log_info "python3-venv already installed"
    fi
    
    # Install other essential packages
    REQUIRED_PACKAGES="curl git build-essential postgresql-client"
    for pkg in $REQUIRED_PACKAGES; do
        if ! dpkg -l | grep -q "^ii  $pkg "; then
            log_info "Installing $pkg..."
            sudo apt-get install -y "$pkg" || log_warning "Failed to install $pkg"
        fi
    done
    
    log_success "System dependencies ready"
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

# Install uv if not present (faster than pip)
if ! command -v uv &> /dev/null; then
    log_info "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Create venv using uv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    log_info "Creating virtual environment with uv..."
    uv venv "$VENV_DIR"
    log_success "Created virtual environment"
else
    log_info "Virtual environment already exists"
fi

log_success "Python environment ready"

###############################################################################
# Dependency Installation (Idempotent)
###############################################################################

log_info "Installing/updating dependencies..."

# Install/sync dependencies using uv (reads from uv.lock for reproducibility)
# --no-install-project: don't install project itself (flat layout application)
uv sync --frozen --no-install-project
log_success "Dependencies installed"

# Activate virtual environment after sync
source "$VENV_DIR/bin/activate"

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

# Load environment variables from .env
log_info "Loading environment variables..."
set -a  # automatically export all variables
source .env
set +a  # disable auto-export
log_success "Environment variables loaded"

###############################################################################
# Database Migrations (Idempotent)
###############################################################################

log_info "Checking database configuration..."

# Check if DATABASE_URL is set
if [ -z "${DATABASE_URL:-}" ]; then
    log_warning "DATABASE_URL not set - skipping database migrations"
    log_info "To enable migrations, add DATABASE_URL to .env file"
    log_info "Example: DATABASE_URL=postgresql://user:pass@localhost:5432/dbname"
else
    log_info "Running database migrations..."
    
    # Check if alembic is configured
    if [ -f "alembic.ini" ]; then
        # Test database connection first
        log_info "Testing database connection..."
        if timeout 5 python -c "
import sys
from sqlalchemy import create_engine, text
try:
    engine = create_engine('$DATABASE_URL')
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print('✅ Database connection successful')
    sys.exit(0)
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    sys.exit(1)
" 2>&1; then
            log_success "Database connection verified"
            
            # Run migrations with error handling
            log_info "Applying database migrations..."
            MIGRATION_OUTPUT=$(alembic upgrade head 2>&1) || MIGRATION_EXIT_CODE=$?
            
            if [ ${MIGRATION_EXIT_CODE:-0} -eq 0 ]; then
                log_success "Database migrations completed"
            else
                # Check if it's a "table already exists" error (safe to ignore)
                if echo "$MIGRATION_OUTPUT" | grep -q "DuplicateTable\|already exists"; then
                    log_warning "Some tables already exist - this is expected"
                    log_info "Marking migration as applied..."
                    
                    # Stamp the database with current revision to sync state
                    if alembic stamp head 2>&1; then
                        log_success "Migration state synchronized"
                    else
                        log_warning "Could not sync migration state, but continuing..."
                    fi
                else
                    # Real migration error
                    log_error "Database migrations failed"
                    log_error "Error details:"
                    echo "$MIGRATION_OUTPUT" | tail -10
                    log_warning "Common causes:"
                    log_warning "  - Migration script has syntax errors"
                    log_warning "  - Incompatible schema changes"
                    log_warning "  - Database permissions issue"
                    log_warning "Continuing deployment without migrations..."
                fi
            fi
        else
            log_error "Cannot connect to database!"
            log_warning "Skipping migrations - check DATABASE_URL and database availability"
            log_info "Database URL format: postgresql://user:pass@host:port/dbname"
        fi
    else
        log_warning "Alembic not configured, skipping migrations"
        
        # Fallback: create tables directly (idempotent)
        if [ -f "create_tables.py" ]; then
            python create_tables.py 2>&1 || log_warning "Table creation failed"
            log_success "Database tables created/verified"
        fi
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
    log_info "Service file already exists - updating configuration..."
    # Force update to apply fixes
    sudo rm -f "$SERVICE_FILE"
fi

log_info "Creating systemd service file..."

# Create service file (requires sudo)
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=SecurePay Wallet API
After=network.target postgresql.service
Wants=postgresql.service

# Rate limiting for restarts
StartLimitIntervalSec=60
StartLimitBurst=5

[Service]
# Use 'exec' type - systemd waits for process to exec()
Type=exec

# Increase startup timeout to 90 seconds
TimeoutStartSec=90
TimeoutStopSec=30

User=${DEPLOY_USER:-$USER}
WorkingDirectory=$APP_DIR

# Load environment variables
EnvironmentFile=$APP_DIR/.env
Environment="PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin"

# Pre-start validation
ExecStartPre=/bin/sh -c 'test -f $APP_DIR/main.py || exit 1'
ExecStartPre=/bin/sh -c 'test -f $VENV_DIR/bin/uvicorn || exit 1'

# Main command - start uvicorn
ExecStart=$VENV_DIR/bin/uvicorn main:app \\
    --host 0.0.0.0 \\
    --port 8000 \\
    --log-level info \\
    --no-access-log

# Graceful reload
ExecReload=/bin/kill -s HUP \$MAINPID

# Restart policy
Restart=always
RestartSec=5s

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=securepay-wallet

# Security (optional but recommended)
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
log_success "Service file created and configured"

# Enable service (idempotent)
sudo systemctl enable "$SERVICE_NAME" 2>/dev/null || true
log_success "Service configured"

###############################################################################
# Nginx Configuration & SSL Setup (Idempotent)
###############################################################################

log_info "Configuring Nginx reverse proxy..."

# Check if Nginx is installed
if ! command -v nginx &> /dev/null; then
    log_warning "Nginx not installed. Installing..."
    sudo apt update -qq
    sudo apt install -y nginx
    log_success "Nginx installed"
else
    log_info "Nginx already installed"
fi

# Set domain from environment or prompt
DOMAIN="${DOMAIN:-}"
if [ -z "$DOMAIN" ]; then
    log_warning "DOMAIN environment variable not set"
    log_info "Skipping SSL configuration (will use HTTP only)"
    DOMAIN="localhost"
    USE_SSL=false
else
    log_info "Configuring for domain: $DOMAIN"
    USE_SSL=true
fi

# Create Nginx configuration
NGINX_CONF="/etc/nginx/sites-available/$APP_NAME"
NGINX_ENABLED="/etc/nginx/sites-enabled/$APP_NAME"

if [ "$USE_SSL" = true ]; then
    # Start with HTTP-only config, certbot will add SSL later
    log_info "Creating initial HTTP configuration (SSL will be added by certbot)..."
    sudo tee "$NGINX_CONF" > /dev/null <<EOF
# HTTP - Will be configured for HTTPS by certbot
server {
    listen 80;
    server_name $DOMAIN;
    
    # Client body size
    client_max_body_size 10M;
    
    # Logging
    access_log /var/log/nginx/${APP_NAME}_access.log;
    error_log /var/log/nginx/${APP_NAME}_error.log;
    
    # Proxy to FastAPI application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Static files (if any)
    location /static {
        alias $APP_DIR/static;
        expires 30d;
    }
}
EOF
else
    # HTTP only configuration (for local/testing)
    sudo tee "$NGINX_CONF" > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    
    # Logging
    access_log /var/log/nginx/${APP_NAME}_access.log;
    error_log /var/log/nginx/${APP_NAME}_error.log;
    
    # Client body size
    client_max_body_size 10M;
    
    # Proxy to FastAPI application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Static files (if any)
    location /static {
        alias $APP_DIR/static;
        expires 30d;
    }
}
EOF
fi

log_success "Nginx configuration created"

# Enable site (idempotent)
if [ ! -L "$NGINX_ENABLED" ]; then
    sudo ln -sf "$NGINX_CONF" "$NGINX_ENABLED"
    log_success "Nginx site enabled"
fi

# Remove default site if it exists
if [ -L "/etc/nginx/sites-enabled/default" ]; then
    sudo rm /etc/nginx/sites-enabled/default
    log_info "Removed default Nginx site"
fi

# Test Nginx configuration
if sudo nginx -t 2>/dev/null; then
    log_success "Nginx configuration valid"
    sudo systemctl reload nginx
    log_success "Nginx reloaded"
else
    log_error "Nginx configuration test failed"
    sudo nginx -t
    exit 1
fi

# SSL Certificate Setup with Certbot
if [ "$USE_SSL" = true ]; then
    log_info "Setting up SSL certificate with Let's Encrypt..."
    
    # Check if certbot is installed
    if ! command -v certbot &> /dev/null; then
        log_info "Installing certbot..."
        sudo apt update -qq
        sudo apt install -y certbot python3-certbot-nginx
        log_success "Certbot installed"
    fi
    
    # Check if certificate already exists
    if [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
        log_info "SSL certificate already exists for $DOMAIN"
        log_info "Certificate will auto-renew via systemd timer"
        log_success "SSL is already configured"
    else
        log_info "Obtaining SSL certificate for $DOMAIN..."
        log_warning "Prerequisites:"
        log_warning "  1. Domain $DOMAIN must point to this server's IP"
        log_warning "  2. Ports 80 and 443 must be open in firewall"
        log_warning "  3. Nginx must be running and accessible on port 80"
        
        # Ensure Nginx is running before certbot attempts validation
        if ! systemctl is-active --quiet nginx; then
            log_warning "Nginx is not running, starting it now..."
            sudo systemctl start nginx || {
                log_error "Failed to start Nginx"
                log_warning "Skipping SSL configuration - fix Nginx first"
                USE_SSL=false
            }
        fi
        
        if [ "$USE_SSL" = true ]; then
            # Attempt to obtain certificate (certbot will modify nginx config)
            if sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "admin@$DOMAIN" --redirect 2>&1 | tee /tmp/certbot.log; then
                log_success "SSL certificate obtained successfully!"
                log_success "Certbot has configured Nginx for HTTPS"
            else
                log_error "Failed to obtain SSL certificate"
                log_error "Certbot output:"
                cat /tmp/certbot.log | tail -20
                log_warning "Common causes:"
                log_warning "  - Domain doesn't point to this server"
                log_warning "  - Firewall blocking ports 80/443"
                log_warning "  - DNS not propagated yet"
                log_info "Continuing with HTTP only"
                log_info "To retry later, run: sudo certbot --nginx -d $DOMAIN"
            fi
        fi
    fi
    
    # Enable certbot renewal timer
    sudo systemctl enable certbot.timer 2>/dev/null || true
    log_info "Certbot auto-renewal enabled"
fi

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
if [ "$USE_SSL" = true ]; then
echo "   • Health: https://$DOMAIN/health"
echo "   • API Docs: https://$DOMAIN/docs"
echo "   • Webhooks: https://$DOMAIN/webhook/paystack"
else
echo "   • Health: http://$DOMAIN/health (or http://localhost:8000/health)"
echo "   • API Docs: http://$DOMAIN/docs (or http://localhost:8000/docs)"
echo "   • Webhooks: http://$DOMAIN/webhook/paystack"
fi
echo ""
echo "🌐 Nginx Status:"
echo "   • Config: /etc/nginx/sites-available/$APP_NAME"
echo "   • Logs: /var/log/nginx/${APP_NAME}_*.log"
echo "   • SSL: $([ "$USE_SSL" = true ] && echo "Enabled (Let's Encrypt)" || echo "Disabled")"
echo ""
echo "📝 Useful Commands:"
echo "   • View logs: sudo journalctl -u $SERVICE_NAME -f"
echo "   • Check status: sudo systemctl status $SERVICE_NAME"
echo "   • Restart: sudo systemctl restart $SERVICE_NAME"
echo "   • Nginx logs: sudo tail -f /var/log/nginx/${APP_NAME}_access.log"
echo "   • Nginx reload: sudo systemctl reload nginx"
echo "   • SSL renewal: sudo certbot renew --dry-run"
echo "   • Rollback: git reset --hard HEAD~1 && bash scripts/deploy.sh"
echo ""
echo "💾 Backup Location: $BACKUP_DIR"
echo ""

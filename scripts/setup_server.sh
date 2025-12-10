#!/bin/bash

###############################################################################
# Initial Server Setup Script
# Run this once on a fresh server to prepare for deployments
###############################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Configuration
APP_NAME="securepay-wallet"
APP_DIR="/opt/securepay-wallet"
APP_USER="securepay"
REPO_URL="https://github.com/yourusername/securepay-wallet.git"

log_info "SecurePay Wallet - Initial Server Setup"
echo ""

###############################################################################
# Check if running as root
###############################################################################

if [ "$EUID" -ne 0 ]; then 
    log_error "Please run as root (use sudo)"
    exit 1
fi

###############################################################################
# System Updates
###############################################################################

log_info "Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq
log_success "System updated"

###############################################################################
# Install Required Packages
###############################################################################

log_info "Installing required packages..."

apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    postgresql \
    postgresql-contrib \
    nginx \
    git \
    curl \
    supervisor \
    certbot \
    python3-certbot-nginx

log_success "Packages installed"

###############################################################################
# Create Application User
###############################################################################

log_info "Creating application user..."

if id "$APP_USER" &>/dev/null; then
    log_info "User $APP_USER already exists"
else
    useradd -m -s /bin/bash "$APP_USER"
    log_success "User $APP_USER created"
fi

###############################################################################
# PostgreSQL Setup
###############################################################################

log_info "Setting up PostgreSQL database..."

# Start PostgreSQL
systemctl start postgresql
systemctl enable postgresql

# Create database and user
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = 'securepay_db'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE securepay_db;"

sudo -u postgres psql -tc "SELECT 1 FROM pg_user WHERE usename = 'securepay_user'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER securepay_user WITH PASSWORD 'CHANGE_THIS_PASSWORD';"

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE securepay_db TO securepay_user;"

log_success "PostgreSQL configured"
log_warning "Remember to change the database password in .env!"

###############################################################################
# Clone Repository
###############################################################################

log_info "Setting up application directory..."

if [ -d "$APP_DIR" ]; then
    log_warning "Directory $APP_DIR already exists"
else
    mkdir -p "$APP_DIR"
    
    # Clone or initialize repository
    if [ -n "$REPO_URL" ]; then
        git clone "$REPO_URL" "$APP_DIR"
    fi
    
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
    log_success "Application directory created"
fi

###############################################################################
# Setup Environment File
###############################################################################

log_info "Creating environment configuration..."

cat > "$APP_DIR/.env" <<EOF
# Database
DATABASE_URL=postgresql://securepay_user:CHANGE_THIS_PASSWORD@localhost/securepay_db

# Security
SECRET_KEY=$(openssl rand -hex 32)

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/google/callback

# Paystack
PAYSTACK_SECRET_KEY=sk_live_your_paystack_secret_key
PAYSTACK_WEBHOOK_SECRET=your_webhook_secret

# Frontend
FRONTEND_URL=https://yourdomain.com

# Environment
ENVIRONMENT=production
EOF

chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"

log_success "Environment file created"
log_warning "Update $APP_DIR/.env with your actual credentials!"

###############################################################################
# Nginx Configuration
###############################################################################

log_info "Configuring Nginx..."

cat > /etc/nginx/sites-available/securepay-wallet <<'EOF'
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /static {
        alias /opt/securepay-wallet/static;
        expires 30d;
    }

    location /webhook/paystack {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Important for webhooks
        proxy_buffering off;
        proxy_request_buffering off;
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/securepay-wallet /etc/nginx/sites-enabled/

# Remove default site
rm -f /etc/nginx/sites-enabled/default

# Test configuration
nginx -t

# Restart Nginx
systemctl restart nginx
systemctl enable nginx

log_success "Nginx configured"

###############################################################################
# Firewall Configuration
###############################################################################

log_info "Configuring firewall..."

if command -v ufw &> /dev/null; then
    ufw --force enable
    ufw allow 22/tcp    # SSH
    ufw allow 80/tcp    # HTTP
    ufw allow 443/tcp   # HTTPS
    log_success "Firewall configured"
fi

###############################################################################
# Setup Scripts Directory
###############################################################################

mkdir -p "$APP_DIR/scripts"
chown "$APP_USER:$APP_USER" "$APP_DIR/scripts"

###############################################################################
# Create Deployment Key
###############################################################################

log_info "Creating deployment SSH key..."

if [ ! -f "/home/$APP_USER/.ssh/id_rsa" ]; then
    sudo -u "$APP_USER" ssh-keygen -t rsa -b 4096 -f "/home/$APP_USER/.ssh/id_rsa" -N ""
    log_success "SSH key created"
    log_warning "Add this public key to your GitHub repository (Deploy Keys):"
    cat "/home/$APP_USER/.ssh/id_rsa.pub"
else
    log_info "SSH key already exists"
fi

###############################################################################
# Summary
###############################################################################

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_success "🎉 Initial setup completed!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 Next Steps:"
echo ""
echo "1. Update configuration:"
echo "   sudo nano $APP_DIR/.env"
echo ""
echo "2. Update Nginx domain:"
echo "   sudo nano /etc/nginx/sites-available/securepay-wallet"
echo "   (Replace 'yourdomain.com' with your actual domain)"
echo ""
echo "3. Setup SSL certificate:"
echo "   sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com"
echo ""
echo "4. Run initial deployment:"
echo "   sudo -u $APP_USER bash $APP_DIR/scripts/deploy.sh"
echo ""
echo "5. Setup GitHub Actions secrets:"
echo "   SSH_PRIVATE_KEY: $(cat /home/$APP_USER/.ssh/id_rsa | base64 -w 0)"
echo "   SERVER_HOST: your-server-ip"
echo "   SERVER_USER: $APP_USER"
echo "   DEPLOY_PATH: $APP_DIR"
echo ""
echo "📊 Service Information:"
echo "   • App Directory: $APP_DIR"
echo "   • App User: $APP_USER"
echo "   • Database: securepay_db"
echo "   • Web Server: Nginx"
echo "   • Service: securepay-wallet"
echo ""

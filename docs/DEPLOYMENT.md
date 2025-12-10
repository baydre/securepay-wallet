# 🚀 Deployment Guide

## Overview

SecurePay Wallet uses a **zero-downtime, idempotent deployment** strategy with automated CI/CD via GitHub Actions.

## Deployment Architecture

```
GitHub Push → GitHub Actions → Run Tests → Deploy to Server → Health Check
                    ↓                              ↓
                 [FAIL] ──────────────────→ Rollback
```

## Prerequisites

### Server Requirements

- **OS**: Ubuntu 20.04+ or Debian 11+
- **RAM**: Minimum 2GB (4GB recommended)
- **Disk**: 20GB minimum
- **CPU**: 2 cores minimum
- **Python**: 3.11+
- **PostgreSQL**: 15+
- **Nginx**: Latest stable

### Required Accounts

1. **GitHub Account** - For repository and Actions
2. **Paystack Account** - For payment processing
3. **Google Cloud Console** - For OAuth
4. **Server/VPS** - DigitalOcean, AWS, Linode, etc.

## Initial Server Setup

### 1. Prepare Server

```bash
# SSH into your server
ssh root@your-server-ip

# Run initial setup script
curl -O https://raw.githubusercontent.com/yourusername/securepay-wallet/main/scripts/setup_server.sh
chmod +x setup_server.sh
sudo bash setup_server.sh
```

This script will:
- Install system dependencies (Python, PostgreSQL, Nginx)
- Create application user and directories
- Setup PostgreSQL database
- Configure Nginx reverse proxy
- Create deployment SSH keys
- Setup firewall rules

### 2. Configure Environment

```bash
# Edit environment file
sudo nano /opt/securepay-wallet/.env
```

**Required Variables:**

```bash
# Database
DATABASE_URL=postgresql://securepay_user:YOUR_PASSWORD@localhost/securepay_db

# Security (auto-generated)
SECRET_KEY=<already set by setup script>

# Google OAuth (from console.cloud.google.com)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/google/callback

# Paystack (from paystack.com)
PAYSTACK_SECRET_KEY=sk_live_your_secret_key
PAYSTACK_WEBHOOK_SECRET=your_webhook_secret

# Frontend
FRONTEND_URL=https://yourdomain.com

# Environment
ENVIRONMENT=production
```

### 3. Setup Domain & SSL

```bash
# Update Nginx configuration with your domain
sudo nano /etc/nginx/sites-available/securepay-wallet
# Replace 'yourdomain.com' with your actual domain

# Test Nginx configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx

# Setup SSL certificate (Let's Encrypt)
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### 4. Initial Deployment

```bash
# Switch to app user
sudo su - securepay

# Navigate to app directory
cd /opt/securepay-wallet

# Run deployment script
bash scripts/deploy.sh
```

## CI/CD Setup

### 1. GitHub Secrets

Add these secrets to your GitHub repository (Settings → Secrets → Actions):

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `SSH_PRIVATE_KEY` | Content of `/home/securepay/.ssh/id_rsa` | For SSH access |
| `SERVER_HOST` | `your-server-ip` | Server IP or domain |
| `SERVER_USER` | `securepay` | Application user |
| `DEPLOY_PATH` | `/opt/securepay-wallet` | Application directory |

**Get SSH private key:**

```bash
# On server
sudo cat /home/securepay/.ssh/id_rsa | base64 -w 0
# Copy the output
```

### 2. Add Deploy Key to GitHub

```bash
# On server, get public key
sudo cat /home/securepay/.ssh/id_rsa.pub
```

Add to GitHub:
1. Repository → Settings → Deploy keys
2. Click "Add deploy key"
3. Paste public key
4. ✅ Enable "Allow write access"

### 3. Configure Paystack Webhook

1. Go to [Paystack Dashboard](https://dashboard.paystack.com)
2. Settings → Webhooks
3. Set URL: `https://yourdomain.com/webhook/paystack`
4. Copy webhook secret to `.env` file

## Deployment Process

### Automatic Deployment (CI/CD)

```bash
# Simply push to main branch
git add .
git commit -m "Your changes"
git push origin main
```

GitHub Actions will:
1. ✅ Run all tests (unit, integration)
2. ✅ Code quality checks (linting)
3. ✅ Security scans
4. ✅ Deploy to server
5. ✅ Run database migrations
6. ✅ Graceful restart
7. ✅ Health check
8. ❌ Rollback on failure

### Manual Deployment

```bash
# SSH into server
ssh securepay@your-server-ip

# Navigate to app directory
cd /opt/securepay-wallet

# Pull latest changes
git pull origin main

# Run deployment script
bash scripts/deploy.sh
```

## Idempotency Features

The deployment script is **idempotent** - safe to run multiple times:

- ✅ **Backups**: Creates timestamped backups before changes
- ✅ **Virtual Environment**: Creates only if missing
- ✅ **Dependencies**: Updates only if changed
- ✅ **Database**: Runs migrations idempotently (Alembic tracks)
- ✅ **Service**: Graceful reload, not restart
- ✅ **Health Checks**: Validates before marking success
- ✅ **Rollback**: Automatic on failure

## Zero-Downtime Deployment

### How It Works

1. **Graceful Reload**: Uses `systemctl reload` instead of `restart`
2. **Health Checks**: Validates service before switching
3. **Rollback**: Automatic revert on failure
4. **Old Process**: Continues serving requests during reload

### Process Flow

```
┌──────────────┐
│ Old Process  │ ─── Serving traffic
└──────────────┘
       │
       ├─── Deploy new code
       │
       ├─── Start new process
       │
┌──────────────┐
│ New Process  │ ─── Health check
└──────────────┘
       │
       ├─── Health check passes
       │
       ├─── Switch traffic to new process
       │
       ├─── Gracefully shutdown old process
       │
       ✅ Zero downtime!
```

## Monitoring & Logs

### View Application Logs

```bash
# Real-time logs
sudo journalctl -u securepay-wallet -f

# Last 100 lines
sudo journalctl -u securepay-wallet -n 100

# Filter by date
sudo journalctl -u securepay-wallet --since "1 hour ago"

# Filter by priority
sudo journalctl -u securepay-wallet -p err
```

### Service Status

```bash
# Check status
sudo systemctl status securepay-wallet

# Check if running
sudo systemctl is-active securepay-wallet
```

### Health Check

```bash
# From server
curl http://localhost:8000/health

# From anywhere
curl https://yourdomain.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "app": "SecurePay Wallet API",
  "version": "1.0.0",
  "database": "connected"
}
```

## Rollback

### Automatic Rollback

If deployment fails, GitHub Actions automatically:
1. Reverts to previous commit
2. Restarts service with old code
3. Notifies in logs

### Manual Rollback

```bash
# SSH into server
ssh securepay@your-server-ip
cd /opt/securepay-wallet

# Rollback to previous commit
git reset --hard HEAD~1

# Or specific commit
git reset --hard <commit-hash>

# Redeploy
bash scripts/deploy.sh
```

### Restore Database Backup

```bash
# List backups
ls -lh backups/

# Restore specific backup
psql $DATABASE_URL < backups/db_backup_20251210_120000.sql
```

## Troubleshooting

### Deployment Failed

```bash
# Check GitHub Actions logs
# Go to: Repository → Actions → Failed workflow

# Check server logs
sudo journalctl -u securepay-wallet -n 50

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Service Won't Start

```bash
# Check service status
sudo systemctl status securepay-wallet

# View full logs
sudo journalctl -u securepay-wallet --no-pager

# Test manually
cd /opt/securepay-wallet
source venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000
```

### Database Connection Issues

```bash
# Test database connection
psql $DATABASE_URL -c "SELECT 1;"

# Check PostgreSQL status
sudo systemctl status postgresql

# Check connection string in .env
cat /opt/securepay-wallet/.env | grep DATABASE_URL
```

### SSL Certificate Issues

```bash
# Check certificate status
sudo certbot certificates

# Renew certificate
sudo certbot renew

# Test renewal
sudo certbot renew --dry-run
```

## Maintenance

### Update Dependencies

```bash
# SSH into server
ssh securepay@your-server-ip
cd /opt/securepay-wallet

# Update requirements.txt in repository first
# Then deploy
git pull origin main
bash scripts/deploy.sh
```

### Database Migrations

```bash
# Create new migration
cd /opt/securepay-wallet
source venv/bin/activate
alembic revision --autogenerate -m "Description"

# Apply migrations (done automatically in deployment)
alembic upgrade head
```

### Backup Strategy

**Automated Backups** (recommended):

```bash
# Add to crontab
crontab -e

# Daily backup at 2 AM
0 2 * * * cd /opt/securepay-wallet && bash scripts/backup.sh
```

**Manual Backup**:

```bash
# Database
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Environment file
cp /opt/securepay-wallet/.env ~/env_backup_$(date +%Y%m%d).env
```

## Performance Optimization

### Enable Gunicorn (Production)

Replace `uvicorn` with `gunicorn` for better performance:

```bash
# Install gunicorn
pip install gunicorn

# Update systemd service
sudo nano /etc/systemd/system/securepay-wallet.service

# Change ExecStart to:
ExecStart=/opt/securepay-wallet/venv/bin/gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8000

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart securepay-wallet
```

### Enable HTTP/2

```bash
# Nginx config
sudo nano /etc/nginx/sites-available/securepay-wallet

# Add 'http2' to listen directive
listen 443 ssl http2;

# Reload Nginx
sudo systemctl reload nginx
```

## Security Checklist

- [ ] SSL certificate installed and auto-renewing
- [ ] Firewall configured (only ports 22, 80, 443 open)
- [ ] Database password changed from default
- [ ] `.env` file permissions set to 600
- [ ] Webhook signature verification enabled
- [ ] Regular security updates scheduled
- [ ] Fail2ban or similar intrusion prevention
- [ ] Regular backups automated
- [ ] Monitoring and alerting setup

## Support

- 📚 **Documentation**: `/docs` directory
- 🐛 **Issues**: GitHub Issues
- 📧 **Contact**: support@yourdomain.com

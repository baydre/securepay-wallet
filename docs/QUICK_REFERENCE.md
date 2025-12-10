# 🚀 Quick Reference Guide

## Common Commands

### Development

```bash
# Start development server
uvicorn main:app --reload

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific tests
pytest tests/unit                    # Unit tests only
pytest tests/integration             # Integration tests
pytest tests/e2e                     # E2E tests
pytest tests/unit/test_auth.py       # Specific file
```

### Database

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show migration history
alembic history
```

### Deployment

```bash
# Initial server setup (run once)
sudo bash scripts/setup_server.sh

# Deploy/update application
sudo -u securepay bash scripts/deploy.sh

# View logs
sudo journalctl -u securepay-wallet -f

# Check service status
sudo systemctl status securepay-wallet

# Restart service
sudo systemctl restart securepay-wallet
```

### Testing Webhooks

```bash
# Start ngrok
ngrok http 8000

# Test webhook with curl
curl -X POST http://localhost:8000/webhook/paystack \
  -H "X-Paystack-Signature: <signature>" \
  -H "Content-Type: application/json" \
  -d '{"event":"charge.success","data":{"reference":"TXN-TEST","amount":100000,"status":"success"}}'
```

## API Endpoints Quick Reference

### Authentication

```bash
# Google OAuth login
GET /auth/google

# OAuth callback
GET /auth/google/callback
```

### Wallet Operations

```bash
# Get wallet info (JWT required)
GET /wallet/

# Get balance (JWT or API key)
GET /wallet/balance

# Deposit funds (JWT or API key with 'deposit')
POST /wallet/deposit
Body: {"amount": 1000.00}

# Check deposit status
GET /wallet/deposit/{reference}/status

# Transfer funds (JWT or API key with 'transfer')
POST /wallet/transfer
Body: {
  "recipient_wallet_number": "WAL0000000001",
  "amount": 500.00,
  "description": "Payment"
}

# Get transactions (with filters)
GET /wallet/transactions?status=success&type=deposit

# Get pending transactions
GET /wallet/transactions/pending

# Get completed transactions
GET /wallet/transactions/completed

# Get transaction summary
GET /wallet/transactions/summary

# Clear old pending transactions
DELETE /wallet/transactions/pending/clear?days_old=1

# Cancel specific transaction
DELETE /wallet/transactions/{reference}/cancel

# Clear all pending (requires confirmation)
DELETE /wallet/transactions/pending/clear-all?confirm=true
```

### API Keys

```bash
# Create API key (JWT required)
POST /keys/create
Body: {
  "name": "My Key",
  "permissions": ["read", "deposit"],
  "expires_in_days": 30
}

# List API keys
GET /keys/

# Delete API key
DELETE /keys/{key_id}
```

### Webhooks

```bash
# Paystack webhook endpoint
POST /webhook/paystack
Headers: X-Paystack-Signature
```

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/db

# Security
SECRET_KEY=<random-secret-32-chars>

# Google OAuth
GOOGLE_CLIENT_ID=<client-id>.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=<client-secret>
GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/google/callback

# Paystack
PAYSTACK_SECRET_KEY=sk_live_<your-key>
PAYSTACK_WEBHOOK_SECRET=<webhook-secret>

# Frontend
FRONTEND_URL=https://yourdomain.com

# Environment
ENVIRONMENT=production
```

## Test Card Details (Paystack)

```
# Successful payment
Card: 4084084084084081
CVV: 408
PIN: 0000
OTP: 123456

# Insufficient funds
Card: 4084080000000409

# Declined
Card: 4084082000000406
```

## GitHub Actions Secrets

```
SSH_PRIVATE_KEY    # Base64 encoded private key
SERVER_HOST        # Server IP or domain
SERVER_USER        # Application user (e.g., securepay)
DEPLOY_PATH        # Application directory (e.g., /opt/securepay-wallet)
```

## File Locations

```
# Application
/opt/securepay-wallet/               # App directory
/opt/securepay-wallet/.env           # Environment config
/opt/securepay-wallet/venv/          # Virtual environment

# Logs
sudo journalctl -u securepay-wallet  # Application logs
/var/log/nginx/access.log            # Nginx access logs
/var/log/nginx/error.log             # Nginx error logs

# Backups
/opt/securepay-wallet/backups/       # Automated backups

# Service
/etc/systemd/system/securepay-wallet.service  # Service config
/etc/nginx/sites-available/securepay-wallet   # Nginx config
```

## Troubleshooting

### Service won't start
```bash
sudo journalctl -u securepay-wallet -n 50
sudo systemctl status securepay-wallet
```

### Database connection issues
```bash
psql $DATABASE_URL -c "SELECT 1;"
```

### Nginx issues
```bash
sudo nginx -t
sudo systemctl status nginx
sudo tail -f /var/log/nginx/error.log
```

### Webhook not working
```bash
# Check Paystack dashboard logs
# Verify signature in code
# Test with curl
```

## Useful Links

- **API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Auth Test Page**: http://localhost:8000/static/auth-test.html

## Documentation Links

- [Complete Deployment Guide](./docs/DEPLOYMENT.md)
- [Testing Guide](./docs/TESTING.md)
- [Webhook Integration](./docs/WEBHOOK_GUIDE.md)
- [Security Best Practices](./docs/SECURITY.md)
- [Troubleshooting](./docs/TROUBLESHOOTING.md)
- [Project Structure](./docs/STRUCTURE.md)
- [Organization Summary](./ORGANIZATION_SUMMARY.md)

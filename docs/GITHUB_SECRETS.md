# GitHub Actions Secrets Setup

This document explains how to configure the required GitHub secrets for CI/CD deployment.

## Required Secrets

Navigate to your repository on GitHub → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

### 1. SSH_PRIVATE_KEY

**Description**: SSH private key for connecting to your production server

**How to generate**:
```bash
# On your local machine
ssh-keygen -t ed25519 -C "github-actions@securepay-wallet" -f ~/.ssh/github_actions

# Copy the private key (this goes to GitHub Secrets)
cat ~/.ssh/github_actions

# Copy the public key to your server
ssh-copy-id -i ~/.ssh/github_actions.pub your_user@your_server.com
```

**GitHub Secret Value**: Paste the entire contents of the private key file (including `-----BEGIN OPENSSH PRIVATE KEY-----` and `-----END OPENSSH PRIVATE KEY-----`)

---

### 2. SERVER_HOST

**Description**: Your production server's hostname or IP address

**Example values**:
- `api.securepay.com`
- `securepay.example.com`
- `123.45.67.89`

**GitHub Secret Value**: `your-server-domain.com`

---

### 3. SERVER_USER

**Description**: SSH user for connecting to the production server

**Example values**:
- `deploy`
- `securepay`
- `ubuntu`
- `www-data`

**GitHub Secret Value**: `deploy` (or your server username)

---

### 4. DEPLOY_PATH

**Description**: Absolute path to the application directory on the server

**Example values**:
- `/home/deploy/securepay-wallet`
- `/var/www/securepay-wallet`
- `/opt/securepay-wallet`

**GitHub Secret Value**: `/home/deploy/securepay-wallet`

---

## Production Environment Variables

These should be set in your **production `.env` file** on the server (not GitHub secrets):

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/securepay_wallet

# JWT Configuration
SECRET_KEY=your-production-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://your-domain.com/auth/google/callback

# Paystack
PAYSTACK_SECRET_KEY=sk_live_xxxxxxxxxxxxx
PAYSTACK_PUBLIC_KEY=pk_live_xxxxxxxxxxxxx
PAYSTACK_WEBHOOK_SECRET=your_paystack_webhook_secret

# Application
APP_NAME=SecurePay Wallet
APP_VERSION=1.0.0
FRONTEND_URL=https://your-frontend-domain.com
BACKEND_URL=https://your-domain.com
```

---

## Verification

After setting up the secrets, verify they're configured correctly:

1. **Check Secrets List**: Go to GitHub → Your Repo → Settings → Secrets and variables → Actions
   - You should see 4 secrets: `SSH_PRIVATE_KEY`, `SERVER_HOST`, `SERVER_USER`, `DEPLOY_PATH`
   - The values are hidden for security

2. **Test SSH Connection Locally**:
   ```bash
   ssh -i ~/.ssh/github_actions your_user@your_server.com "echo 'SSH connection successful!'"
   ```

3. **Test Deployment** (push to main branch):
   ```bash
   git add .
   git commit -m "Test CI/CD pipeline"
   git push origin main
   ```

4. **Monitor Deployment**: Go to GitHub → Your Repo → Actions tab
   - Watch the pipeline run through all jobs: test → lint → security → deploy
   - Check logs if any job fails

---

## CI/CD Pipeline Overview

The pipeline uses **uv** for fast dependency installation and runs:

### Stage 0 (Parallel)
1. **Test Job** - Runs unit and integration tests with PostgreSQL
2. **Lint Job** - Checks code quality (Black, isort, Flake8)
3. **Security Job** - Scans for vulnerabilities (Safety, Bandit)

### Stage 1 (After Stage 0 passes)
4. **Deploy Job** - Only on `main` branch push
   - SSH into production server
   - Pull latest code
   - Install dependencies with `uv`
   - Run database migrations
   - Graceful restart with zero downtime
   - Health check verification
   - Auto-rollback on failure

---

## Troubleshooting

### SSH Connection Failed
```
Error: Permission denied (publickey)
```

**Solution**: Ensure the public key is in your server's `~/.ssh/authorized_keys`:
```bash
# On your server
mkdir -p ~/.ssh
chmod 700 ~/.ssh
cat >> ~/.ssh/authorized_keys
# Paste the public key content here, then Ctrl+D
chmod 600 ~/.ssh/authorized_keys
```

---

### Deployment Health Check Failed
```
Error: curl -f http://localhost:8000/health || exit 1
```

**Solution**:
1. Check if the server is running: `sudo systemctl status securepay-wallet`
2. Check application logs: `sudo journalctl -u securepay-wallet -n 50`
3. Verify `.env` file has all required variables
4. Ensure PostgreSQL is running and accessible

---

### Database Migration Failed
```
Error: alembic upgrade head
```

**Solution**:
1. Check database connection: `psql $DATABASE_URL`
2. Verify Alembic is installed: `alembic --version`
3. Check migration files exist: `ls alembic/versions/`
4. Run migrations manually: `cd /path/to/app && source venv/bin/activate && alembic upgrade head`

---

## Security Best Practices

1. **Rotate SSH Keys Regularly**: Generate new keys every 6-12 months
2. **Use Separate Keys**: Don't reuse personal SSH keys for CI/CD
3. **Monitor Failed Logins**: Check server logs for unauthorized access attempts
4. **Enable 2FA on GitHub**: Protect your repository and secrets
5. **Restrict SSH Access**: Use firewall rules to limit SSH access to trusted IPs
6. **Use Strong Secrets**: Generate cryptographically secure secrets for JWT and Paystack

---

## Next Steps

After setting up GitHub secrets:

1. ✅ Push code to `main` branch to trigger deployment
2. ✅ Monitor the Actions tab for pipeline execution
3. ✅ Verify application is running: `curl https://your-domain.com/health`
4. ✅ Test Paystack webhooks with your production webhook URL
5. ✅ Configure Nginx SSL with Let's Encrypt (see DEPLOYMENT.md)

For more details, see:
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Complete deployment guide
- [WEBHOOK_GUIDE.md](./WEBHOOK_GUIDE.md) - Webhook setup and testing

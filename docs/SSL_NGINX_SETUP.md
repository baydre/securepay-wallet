# Nginx + SSL Configuration Guide

## Overview

The deployment script automatically configures Nginx as a reverse proxy with optional SSL/TLS certificates from Let's Encrypt.

## Features

✅ **Automatic Nginx installation** - Installs if not present  
✅ **Reverse proxy configuration** - Routes traffic from Nginx to FastAPI (port 8000)  
✅ **SSL/TLS certificates** - Free Let's Encrypt certificates via certbot  
✅ **Auto-renewal** - Certificates renew automatically every 90 days  
✅ **Security headers** - HSTS, X-Frame-Options, CSP, etc.  
✅ **HTTP → HTTPS redirect** - Automatic upgrade to secure connection  
✅ **Static file serving** - Optimized caching for static assets  

## Prerequisites

### 1. Domain Name
- You need a domain pointing to your server's IP address
- Example: `api.yourdomain.com` → `203.0.113.10`
- Configure DNS A record before deployment

### 2. Firewall Ports
Ensure these ports are open:
```bash
sudo ufw allow 80/tcp   # HTTP (for Let's Encrypt validation)
sudo ufw allow 443/tcp  # HTTPS
sudo ufw allow 22/tcp   # SSH (for deployment)
```

### 3. Server Requirements
- Ubuntu 20.04+ or Debian 10+
- Root or sudo access
- At least 512MB RAM

## Deployment with SSL

### Option 1: Via CI/CD (Recommended)

Add the `DOMAIN` environment variable to your GitHub Actions workflow:

```yaml
- name: Deploy application
  env:
    DOMAIN: api.yourdomain.com  # Add this line
    SERVER_HOST: ${{ secrets.SERVER_HOST }}
    SERVER_USER: ${{ secrets.SERVER_USER }}
    DEPLOY_PATH: ${{ secrets.DEPLOY_PATH }}
```

Or add to GitHub Secrets:
- `DOMAIN` = `api.yourdomain.com`

### Option 2: Manual Deployment

Set the domain before running the script:

```bash
export DOMAIN=api.yourdomain.com
bash scripts/deploy.sh
```

### Option 3: HTTP Only (No SSL)

If you don't set `DOMAIN`, the script will configure HTTP only:

```bash
# DOMAIN not set - uses HTTP on localhost
bash scripts/deploy.sh
```

This is useful for:
- Local development
- Internal networks
- Behind a separate load balancer with SSL termination

## SSL Certificate Process

The script uses **certbot** to obtain free certificates from Let's Encrypt:

1. **First deployment** (no certificate):
   ```
   📦 Installing Nginx...
   🔒 Obtaining SSL certificate for api.yourdomain.com...
   ✅ SSL certificate obtained successfully!
   ```

2. **Subsequent deployments** (certificate exists):
   ```
   ✅ SSL certificate already exists for api.yourdomain.com
   ℹ️  Certificate will auto-renew via systemd timer
   ```

3. **Auto-renewal**:
   - Certbot creates a systemd timer that runs twice daily
   - Automatically renews certificates 30 days before expiry
   - No manual intervention needed

## Certificate Management

### Check Certificate Status
```bash
sudo certbot certificates
```

Output:
```
Certificate Name: api.yourdomain.com
  Domains: api.yourdomain.com
  Expiry Date: 2025-03-10 12:34:56+00:00 (VALID: 89 days)
  Certificate Path: /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem
  Private Key Path: /etc/letsencrypt/live/api.yourdomain.com/privkey.pem
```

### Test Auto-Renewal
```bash
sudo certbot renew --dry-run
```

### Manual Renewal (if needed)
```bash
sudo certbot renew
sudo systemctl reload nginx
```

### Revoke Certificate
```bash
sudo certbot revoke --cert-path /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem
```

## Nginx Configuration

### View Current Config
```bash
sudo cat /etc/nginx/sites-available/securepay-wallet
```

### Test Configuration
```bash
sudo nginx -t
```

### Reload Nginx
```bash
sudo systemctl reload nginx
```

### View Logs
```bash
# Access logs
sudo tail -f /var/log/nginx/securepay-wallet_access.log

# Error logs
sudo tail -f /var/log/nginx/securepay-wallet_error.log
```

## Troubleshooting

### Certificate Validation Fails

**Error**: `Failed to obtain SSL certificate`

**Solutions**:

1. **Check DNS**:
   ```bash
   dig +short api.yourdomain.com
   # Should return your server's IP
   ```

2. **Check firewall**:
   ```bash
   sudo ufw status
   # Ensure ports 80 and 443 are open
   ```

3. **Check Nginx is running**:
   ```bash
   sudo systemctl status nginx
   ```

4. **Check Let's Encrypt rate limits**:
   - 50 certificates per domain per week
   - 5 duplicate certificates per week
   - Wait or use staging environment for testing

5. **Manual certificate request**:
   ```bash
   sudo certbot --nginx -d api.yourdomain.com
   ```

### Nginx Configuration Errors

**Error**: `nginx: configuration file test failed`

**Solution**:
```bash
# Check syntax errors
sudo nginx -t

# View detailed error
sudo journalctl -u nginx -n 50

# Restore previous config if needed
sudo cp /etc/nginx/sites-available/securepay-wallet.bak /etc/nginx/sites-available/securepay-wallet
sudo systemctl reload nginx
```

### 502 Bad Gateway

**Cause**: Nginx can't connect to FastAPI app on port 8000

**Solutions**:

1. **Check FastAPI is running**:
   ```bash
   sudo systemctl status securepay-wallet
   curl http://localhost:8000/health
   ```

2. **Check port binding**:
   ```bash
   sudo netstat -tlnp | grep 8000
   # Should show uvicorn listening
   ```

3. **Check SELinux** (if applicable):
   ```bash
   sudo setsebool -P httpd_can_network_connect 1
   ```

### Certificate Renewal Fails

**Solution**:
```bash
# Check renewal timer is active
sudo systemctl status certbot.timer

# Enable if disabled
sudo systemctl enable --now certbot.timer

# Check renewal logs
sudo journalctl -u certbot -n 50
```

## Security Best Practices

### 1. Keep Software Updated
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Monitor Certificate Expiry
Set up monitoring alerts 30 days before expiry:
```bash
# Add to crontab
0 0 * * * certbot certificates | grep -q "VALID: [0-3][0-9] days" && echo "Certificate expiring soon" | mail -s "SSL Alert" admin@yourdomain.com
```

### 3. Enable UFW Firewall
```bash
sudo ufw enable
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

### 4. Regular Security Audits
```bash
# Check SSL configuration
curl -I https://api.yourdomain.com

# SSL Labs test (external)
# Visit: https://www.ssllabs.com/ssltest/
```

### 5. Monitor Nginx Logs
```bash
# Watch for suspicious activity
sudo tail -f /var/log/nginx/securepay-wallet_access.log | grep -E "40[0-9]|50[0-9]"
```

## Advanced Configuration

### Custom SSL Certificate

If you have your own certificate (not Let's Encrypt):

1. Copy certificates to server:
   ```bash
   sudo cp your-cert.pem /etc/ssl/certs/securepay-wallet.pem
   sudo cp your-key.pem /etc/ssl/private/securepay-wallet.key
   ```

2. Update Nginx config:
   ```nginx
   ssl_certificate /etc/ssl/certs/securepay-wallet.pem;
   ssl_certificate_key /etc/ssl/private/securepay-wallet.key;
   ```

3. Reload Nginx:
   ```bash
   sudo systemctl reload nginx
   ```

### Multiple Domains

To serve multiple domains:

1. Update Nginx config:
   ```nginx
   server_name api.yourdomain.com app.yourdomain.com;
   ```

2. Obtain multi-domain certificate:
   ```bash
   sudo certbot --nginx -d api.yourdomain.com -d app.yourdomain.com
   ```

### Rate Limiting

Add to Nginx config to prevent abuse:

```nginx
# In http block
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

# In server block
location / {
    limit_req zone=api burst=20 nodelay;
    proxy_pass http://127.0.0.1:8000;
}
```

## Architecture Diagram

```
┌─────────────────┐
│   Internet      │
└────────┬────────┘
         │ HTTPS (443)
         ▼
┌─────────────────┐
│  Nginx (80/443) │  ◄─── SSL termination
│  Reverse Proxy  │  ◄─── Security headers
└────────┬────────┘  ◄─── Static files
         │ HTTP (localhost:8000)
         ▼
┌─────────────────┐
│  FastAPI App    │  ◄─── Your application
│  (uvicorn)      │
└─────────────────┘
```

## Production Checklist

Before going live:

- [ ] Domain DNS configured correctly
- [ ] Firewall ports 80, 443 open
- [ ] SSL certificate obtained
- [ ] Certificate auto-renewal working
- [ ] Nginx logs rotating properly
- [ ] Health checks passing
- [ ] Application environment variables set
- [ ] Database backups configured
- [ ] Monitoring/alerting configured
- [ ] Documentation updated with domain

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DOMAIN` | No | `localhost` | Your domain name for SSL |
| `DEPLOY_PATH` | No | `/opt/securepay-wallet` | App directory |
| `DEPLOY_USER` | No | `$USER` | System user for service |

## Resources

- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Certbot Documentation](https://certbot.eff.org/docs/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [SSL Labs Server Test](https://www.ssllabs.com/ssltest/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)

## Support

If you encounter issues:

1. Check logs: `sudo journalctl -u securepay-wallet -n 100`
2. Check Nginx: `sudo nginx -t && sudo systemctl status nginx`
3. Check certificates: `sudo certbot certificates`
4. Review this guide's troubleshooting section
5. Check firewall: `sudo ufw status`

For security issues, please report privately.

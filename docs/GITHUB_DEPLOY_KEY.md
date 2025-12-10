# GitHub Deploy Key Setup Guide

## Overview

This guide explains how to set up a GitHub deploy key so your server can clone/pull from your private repository during CI/CD deployments.

## Why Do We Need This?

When the deployment workflow runs:
1. GitHub Actions runner connects to your server via SSH ✅
2. On the server, it runs `git clone git@github.com:...` ❌
3. Your server needs its own SSH key to authenticate with GitHub

## Setup Steps

### Step 1: Generate SSH Key Pair

On your **local machine** (not the server), generate a new SSH key pair:

```bash
# Generate a new SSH key specifically for deployments
ssh-keygen -t ed25519 -C "deploy@securepay-wallet" -f ~/.ssh/github_deploy_key

# This creates two files:
# ~/.ssh/github_deploy_key       (private key - keep secret!)
# ~/.ssh/github_deploy_key.pub   (public key - add to GitHub)
```

**Important**: Don't use a passphrase when prompted (just press Enter), as the key will be used in automated deployments.

### Step 2: Add Public Key to GitHub

1. **Copy the public key**:
   ```bash
   cat ~/.ssh/github_deploy_key.pub
   ```

2. **Add to GitHub Repository**:
   - Go to your repository on GitHub
   - Navigate to: `Settings` → `Deploy keys` → `Add deploy key`
   - **Title**: `Production Server Deploy Key`
   - **Key**: Paste the public key content
   - ✅ Check "Allow write access" (if you need push access)
   - Click **Add key**

   **URL**: `https://github.com/baydre/securepay-wallet/settings/keys`

### Step 3: Add Private Key to GitHub Secrets

1. **Copy the private key** (entire content including BEGIN/END lines):
   ```bash
   cat ~/.ssh/github_deploy_key
   ```

2. **Add to GitHub Actions Secrets**:
   - Go to your repository on GitHub
   - Navigate to: `Settings` → `Secrets and variables` → `Actions`
   - Click **New repository secret**
   - **Name**: `GITHUB_DEPLOY_KEY`
   - **Value**: Paste the entire private key content
   - Click **Add secret**

   **URL**: `https://github.com/baydre/securepay-wallet/settings/secrets/actions`

### Step 4: Verify Setup

Your GitHub Actions workflow will now automatically:
1. Copy the deploy key to your server
2. Configure Git to use it for github.com
3. Add github.com to known_hosts
4. Clone/fetch using the deploy key

## Security Notes

### ✅ Good Practices

- **Separate keys**: Use a dedicated key for deployments (not your personal GitHub key)
- **Read-only**: If you only need to pull code, don't check "Allow write access"
- **One key per environment**: Use different keys for staging/production
- **Rotate regularly**: Change deploy keys every 90-180 days

### ⚠️ Important

- **Never commit** the private key to your repository
- **Never share** the private key in chat/email
- **Delete old keys** from GitHub when no longer needed
- **Monitor access**: GitHub shows when deploy keys are used

### 🔒 Key Storage

The deployment workflow stores the key on your server at:
```
~/.ssh/github_deploy_key
```

This is configured in:
```
~/.ssh/config
```

## Troubleshooting

### "Permission denied (publickey)"

**Cause**: Deploy key not added to GitHub or private key incorrect

**Solutions**:
1. Verify public key is added to GitHub deploy keys
2. Check private key in GitHub Secrets is complete (including BEGIN/END lines)
3. Ensure no extra spaces/newlines in the secret
4. Test on server:
   ```bash
   ssh -i ~/.ssh/github_deploy_key git@github.com
   # Should say: "Hi baydre/securepay-wallet! You've successfully authenticated..."
   ```

### "Host key verification failed"

**Cause**: github.com not in server's known_hosts

**Solution**: The workflow automatically adds it, but you can manually add:
```bash
ssh your-server "ssh-keyscan -H github.com >> ~/.ssh/known_hosts"
```

### "Bad owner or permissions"

**Cause**: SSH key file has wrong permissions

**Solution**: The workflow sets correct permissions, but verify:
```bash
ssh your-server "chmod 600 ~/.ssh/github_deploy_key ~/.ssh/config"
```

### Key Not Working After Setup

**Debug steps**:

1. **Check key on server**:
   ```bash
   ssh $SERVER_USER@$SERVER_HOST "ls -la ~/.ssh/"
   # Should show: github_deploy_key with permissions 600
   ```

2. **Test GitHub connection from server**:
   ```bash
   ssh $SERVER_USER@$SERVER_HOST "ssh -T git@github.com"
   # Should authenticate successfully
   ```

3. **Check SSH config**:
   ```bash
   ssh $SERVER_USER@$SERVER_HOST "cat ~/.ssh/config"
   # Should show Host github.com configuration
   ```

4. **Test git clone**:
   ```bash
   ssh $SERVER_USER@$SERVER_HOST "cd /tmp && git clone git@github.com:baydre/securepay-wallet.git test-clone"
   # Should clone successfully
   ```

## Revoking Access

### When to Revoke

- Key is compromised
- Team member leaves
- Server is decommissioned
- Regular security rotation

### How to Revoke

1. **Remove from GitHub**:
   - Go to: `Settings` → `Deploy keys`
   - Click the key
   - Click **Delete**

2. **Remove from server**:
   ```bash
   ssh $SERVER_USER@$SERVER_HOST "rm -f ~/.ssh/github_deploy_key"
   ```

3. **Remove from GitHub Secrets**:
   - Go to: `Settings` → `Secrets and variables` → `Actions`
   - Find `GITHUB_DEPLOY_KEY`
   - Click **Remove**

## Alternative: HTTPS with Token

If you prefer not to use SSH deploy keys, you can use HTTPS with a Personal Access Token (PAT):

1. **Generate PAT**: `Settings` → `Developer settings` → `Personal access tokens` → `Tokens (classic)`
2. **Add as secret**: Name it `GITHUB_TOKEN`
3. **Update workflow** to use HTTPS:
   ```bash
   git clone https://x-access-token:${{ secrets.GITHUB_TOKEN }}@github.com/${{ github.repository }}.git .
   ```

## Workflow Integration

The deploy key is automatically configured by this step in `.github/workflows/ci-cd.yml`:

```yaml
- name: Setup GitHub access on server
  env:
    SERVER_HOST: ${{ secrets.SERVER_HOST }}
    SERVER_USER: ${{ secrets.SERVER_USER }}
  run: |
    # Copy deploy key
    ssh $SERVER_USER@$SERVER_HOST "mkdir -p ~/.ssh && chmod 700 ~/.ssh"
    echo "${{ secrets.GITHUB_DEPLOY_KEY }}" | ssh $SERVER_USER@$SERVER_HOST "cat > ~/.ssh/github_deploy_key && chmod 600 ~/.ssh/github_deploy_key"
    
    # Configure git
    ssh $SERVER_USER@$SERVER_HOST 'echo "Host github.com" > ~/.ssh/config'
    ssh $SERVER_USER@$SERVER_HOST 'echo "  IdentityFile ~/.ssh/github_deploy_key" >> ~/.ssh/config'
    ssh $SERVER_USER@$SERVER_HOST "chmod 600 ~/.ssh/config"
```

## Required GitHub Secrets

After following this guide, you should have these secrets configured:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `SSH_PRIVATE_KEY` | Key for accessing your server | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `GITHUB_DEPLOY_KEY` | Key for GitHub access from server | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `SERVER_HOST` | Your server's hostname/IP | `203.0.113.10` or `api.yourdomain.com` |
| `SERVER_USER` | SSH username on server | `ubuntu` or `deploy` |
| `DEPLOY_PATH` | Application directory path | `/opt/securepay-wallet` |

## Quick Reference

```bash
# Generate key
ssh-keygen -t ed25519 -C "deploy@securepay-wallet" -f ~/.ssh/github_deploy_key

# View public key (add to GitHub Deploy Keys)
cat ~/.ssh/github_deploy_key.pub

# View private key (add to GitHub Secrets as GITHUB_DEPLOY_KEY)
cat ~/.ssh/github_deploy_key

# Test from server
ssh your-server "ssh -T git@github.com"

# Debug
ssh your-server "GIT_SSH_COMMAND='ssh -vvv' git clone git@github.com:baydre/securepay-wallet.git /tmp/test"
```

## Resources

- [GitHub Deploy Keys Documentation](https://docs.github.com/en/developers/overview/managing-deploy-keys)
- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [SSH Key Types](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent)

# 📁 Project Structure

## Overview

SecurePay Wallet is organized into a clean, maintainable structure following best practices.

```
securepay-wallet/
├── .github/
│   └── workflows/
│       └── ci-cd.yml          # GitHub Actions CI/CD pipeline
├── alembic/                   # Database migrations
│   ├── versions/              # Migration scripts
│   └── env.py                 # Alembic configuration
├── docs/                      # 📚 Documentation
│   ├── DEPLOYMENT.md          # Deployment guide
│   ├── TESTING.md             # Testing guide
│   ├── WEBHOOK_GUIDE.md       # Paystack webhook documentation
│   ├── SECURITY.md            # Security best practices
│   ├── TROUBLESHOOTING.md     # Common issues and solutions
│   └── PENDING_TRANSACTIONS.md # Transaction management guide
├── routers/                   # 🛣️ API Routes
│   ├── auth_routes.py         # Google OAuth endpoints
│   ├── keys_routes.py         # API key management
│   ├── wallet_routes.py       # Wallet operations
│   └── webhook_routes.py      # Paystack webhooks
├── services/                  # 🔧 Business Logic
│   └── paystack.py            # Paystack integration
├── scripts/                   # 🚀 Deployment Scripts
│   ├── deploy.sh              # Idempotent deployment script
│   └── setup_server.sh        # Initial server setup
├── static/                    # 📄 Static Files
│   └── auth-test.html         # OAuth testing page
├── tests/                     # 🧪 Test Suite
│   ├── unit/                  # Unit tests (fast, isolated)
│   │   ├── test_auth.py       # Auth functions
│   │   ├── test_models.py     # Database models
│   │   └── test_paystack.py   # Paystack service
│   ├── integration/           # Integration tests (API)
│   │   └── test_wallet_api.py # Wallet endpoints
│   ├── e2e/                   # End-to-end tests
│   │   ├── test_api.py        # Interactive API test
│   │   └── test_full_workflow.py # Complete user flow
│   └── conftest.py            # Test fixtures & config
├── auth.py                    # 🔐 Authentication logic
├── config.py                  # ⚙️ Configuration management
├── database.py                # 🗄️ Database connection
├── dependencies.py            # 📦 FastAPI dependencies
├── models.py                  # 📊 SQLAlchemy models
├── schemas.py                 # 📋 Pydantic schemas
├── main.py                    # 🚀 FastAPI application
├── requirements.txt           # 📦 Python dependencies
├── alembic.ini                # Alembic configuration
├── .env.example               # Environment template
├── .gitignore                 # Git ignore rules
└── README.md                  # Project documentation
```

## Directory Details

### `/routers` - API Endpoints

Contains all API route handlers organized by feature:

- **auth_routes.py**: Google OAuth login/callback
- **keys_routes.py**: API key CRUD operations
- **wallet_routes.py**: Wallet operations (deposit, transfer, balance, transactions)
- **webhook_routes.py**: Paystack webhook handler

### `/services` - External Integrations

Business logic and third-party service integrations:

- **paystack.py**: Payment gateway integration
  - Transaction initialization
  - Verification
  - Webhook signature validation

### `/tests` - Test Suite

Comprehensive test coverage organized by type:

- **unit/**: Fast, isolated tests (< 1s each)
- **integration/**: API endpoint tests
- **e2e/**: Full user workflow tests
- **conftest.py**: Shared fixtures and configuration

See [TESTING.md](./docs/TESTING.md) for details.

### `/scripts` - Automation

Deployment and maintenance scripts:

- **deploy.sh**: Idempotent deployment (safe to run multiple times)
- **setup_server.sh**: Initial server configuration

### `/docs` - Documentation

Comprehensive guides for development and operations:

- **DEPLOYMENT.md**: Complete deployment guide with CI/CD
- **TESTING.md**: Testing strategy and guidelines
- **WEBHOOK_GUIDE.md**: Paystack webhook integration
- **SECURITY.md**: Security best practices
- **TROUBLESHOOTING.md**: Common issues and fixes
- **PENDING_TRANSACTIONS.md**: Transaction management

### `/alembic` - Database Migrations

Version-controlled database schema changes:

- Each migration is timestamped and reversible
- Run with: `alembic upgrade head`
- Create new: `alembic revision --autogenerate -m "message"`

### `/.github/workflows` - CI/CD

Automated testing and deployment:

- Runs tests on every push/PR
- Deploys to production on main branch
- Includes security scanning and linting

## Core Files

### Application Entry Point

- **main.py**: FastAPI app initialization, middleware, route registration

### Data Layer

- **models.py**: SQLAlchemy ORM models (User, Wallet, Transaction, APIKey)
- **schemas.py**: Pydantic validation schemas (requests/responses)
- **database.py**: Database connection and session management

### Security

- **auth.py**: JWT tokens, API key hashing, OAuth helpers
- **dependencies.py**: FastAPI dependency injection for auth

### Configuration

- **config.py**: Environment variable management using Pydantic
- **.env**: Environment-specific configuration (not in git)
- **.env.example**: Template for environment variables

## File Naming Conventions

### Python Files

- **snake_case** for all Python files: `wallet_routes.py`, `test_auth.py`
- **Prefix with `test_`** for test files: `test_wallet_api.py`

### Routes

- **Suffix with `_routes`**: `auth_routes.py`, `wallet_routes.py`
- Each file contains one `APIRouter` instance

### Tests

- **test_*.py** for test files
- **Test classes**: `TestWalletEndpoints`, `TestPasswordHashing`
- **Test functions**: `test_create_wallet_success()`

## Import Structure

### Standard Library
```python
import json
from datetime import datetime, timedelta
from typing import List, Optional
```

### Third-Party
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import bcrypt
```

### Local
```python
import models
from schemas import DepositRequest, DepositResponse
from dependencies import get_db, get_current_user
from services.paystack import PaystackService
```

## Configuration Management

### Environment Variables

Stored in `.env` (local) or GitHub Secrets (CI/CD):

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/db

# Security
SECRET_KEY=random-secret-key

# OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# Paystack
PAYSTACK_SECRET_KEY=sk_live_...
PAYSTACK_WEBHOOK_SECRET=...
```

### Access in Code

```python
from config import get_settings

settings = get_settings()
secret_key = settings.paystack_secret_key
```

## Adding New Features

### 1. Create Route Handler

```python
# routers/new_feature_routes.py
from fastapi import APIRouter, Depends
import models
from dependencies import get_db, get_current_user

router = APIRouter(prefix="/feature", tags=["Feature"])

@router.get("/")
async def get_feature(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return {"message": "New feature"}
```

### 2. Register Router

```python
# main.py
from routers import new_feature_routes

app.include_router(new_feature_routes.router)
```

### 3. Add Tests

```python
# tests/integration/test_new_feature.py
def test_get_feature(client, auth_headers):
    response = client.get("/feature/", headers=auth_headers)
    assert response.status_code == 200
```

### 4. Update Documentation

- Add endpoint to README.md
- Create guide in `/docs` if complex
- Update API docs (automatic via FastAPI)

## Best Practices

### Code Organization

- ✅ One router per feature/resource
- ✅ Keep route handlers thin (use services for logic)
- ✅ Use dependency injection for shared logic
- ✅ Type hints on all functions
- ✅ Docstrings for complex functions

### Database

- ✅ Use Alembic for all schema changes
- ✅ Never modify database directly in production
- ✅ Test migrations on staging first
- ✅ Keep models.py synchronized with database

### Testing

- ✅ Unit tests for business logic
- ✅ Integration tests for API endpoints
- ✅ E2E tests for critical flows
- ✅ Mock external services (Paystack, Google)

### Documentation

- ✅ Update docs when adding features
- ✅ Keep README.md current
- ✅ Add docstrings to complex functions
- ✅ Include examples in docs

## Maintenance Tasks

### Regular Updates

```bash
# Update dependencies
pip install --upgrade -r requirements.txt
pip freeze > requirements.txt

# Run tests
pytest

# Check security
safety check
bandit -r .

# Format code
black .
isort .
```

### Database Maintenance

```bash
# Create migration after model changes
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

### Log Rotation

```bash
# Logs are managed by systemd/journald
# Configure retention in /etc/systemd/journald.conf
```

## Getting Help

- 📚 **Documentation**: See `/docs` directory
- 🧪 **Tests**: See `/tests` for examples
- 🐛 **Issues**: Check TROUBLESHOOTING.md
- 💬 **Support**: Create GitHub issue

## Contributing

1. Create feature branch from `develop`
2. Make changes following conventions above
3. Add tests for new features
4. Update documentation
5. Create pull request to `develop`
6. CI runs tests automatically
7. Merge after review + passing tests

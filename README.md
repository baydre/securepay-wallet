# SecurePay Wallet API

A production-ready, secure digital wallet system built with FastAPI, featuring Google OAuth authentication, Paystack payment integration, comprehensive testing, and automated CI/CD.

## 🌟 Features

- 🔐 **Dual Authentication System**
  - Google OAuth 2.0 with JWT tokens (30-minute expiry)
  - API key authentication with granular permissions (read, deposit, transfer)
  - Secure bcrypt hashing with SHA256 pre-hashing

- 💰 **Wallet Operations**
  - Deposit funds via Paystack with real-time webhooks
  - Transfer funds between wallets
  - Check balance and transaction history
  - Filter transactions by status and type
  - View pending/completed transactions separately
  - Transaction summary statistics

- 🔑 **API Key Management**
  - Create up to 5 API keys per user
  - Granular permissions (read, deposit, transfer)
  - Key expiration and automatic cleanup
  - Secure key generation with `sk_` prefix

- 🔔 **Webhook Integration**
  - Secure Paystack webhook handling with HMAC SHA512 verification
  - Idempotent transaction processing (prevents double-crediting)
  - Automatic wallet crediting on successful payments
  - Comprehensive error handling and logging

- 🛡️ **Security Features**
  - JWT token authentication with automatic expiry
  - API key SHA256 + bcrypt hashing
  - Webhook signature verification
  - Input validation with Pydantic v2
  - Timezone-aware datetime handling
  - SQL injection protection via ORM

- 🧪 **Testing & Quality**
  - 30+ unit tests for core functionality
  - Integration tests for all API endpoints
  - End-to-end workflow tests
  - Code coverage tracking
  - Automated testing in CI/CD

- 🚀 **DevOps & Deployment**
  - GitHub Actions CI/CD pipeline
  - Zero-downtime deployments
  - Idempotent deployment scripts
  - Automated database migrations
  - Health checks and rollback capabilities

## 📁 Project Structure

```
securepay-wallet/
├── docs/                          # 📚 Comprehensive documentation
│   ├── DEPLOYMENT.md              # Production deployment guide
│   ├── TESTING.md                 # Testing strategy & guide
│   ├── WEBHOOK_GUIDE.md           # Paystack webhook integration
│   ├── PAYMENT_CALLBACK.md        # Payment callback handling
│   ├── GITHUB_SECRETS.md          # CI/CD secrets setup
│   ├── SECURITY.md                # Security best practices
│   ├── TROUBLESHOOTING.md         # Common issues & solutions
│   ├── STRUCTURE.md               # Project structure details
│   ├── PENDING_TRANSACTIONS.md    # Transaction management
│   ├── QUICK_REFERENCE.md         # Quick command reference
│   └── ORGANIZATION_SUMMARY.md    # Project organization
├── tests/                         # 🧪 42+ tests (100% organized)
│   ├── conftest.py                # Shared fixtures
│   ├── unit/                      # Unit tests (29 tests)
│   │   ├── test_auth.py           # Auth functions
│   │   ├── test_models.py         # Database models
│   │   └── test_paystack.py       # Paystack service
│   ├── integration/               # Integration tests (11 tests)
│   │   └── test_wallet_api.py     # API endpoints
│   └── e2e/                       # End-to-end tests (2 tests)
│       ├── test_api.py            # Interactive testing
│       └── test_full_workflow.py  # Complete user flow
├── routers/                       # 🛣️ API route handlers
│   ├── auth_routes.py             # Google OAuth
│   ├── keys_routes.py             # API key management
│   ├── wallet_routes.py           # Wallet operations
│   └── webhook_routes.py          # Paystack webhooks
├── services/                      # 🔧 Business logic
│   └── paystack.py                # Payment gateway integration
├── scripts/                       # 🚀 Deployment automation
│   ├── setup.sh                   # Local development setup
│   ├── deploy.sh                  # Idempotent deployment
│   └── setup_server.sh            # Initial server setup
├── static/                        # 🎨 Static assets
│   └── payment-success.html       # Payment status page
├── .github/workflows/             # ⚙️ CI/CD pipeline (uses uv)
│   └── ci-cd.yml                  # Automated testing & deployment
└── [core files]                   # Main application code
```

**See [docs/STRUCTURE.md](./docs/STRUCTURE.md) for complete details.**

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: Google OAuth 2.0, JWT, API Keys
- **Payment Gateway**: Paystack
- **Validation**: Pydantic
- **Rate Limiting**: SlowAPI

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Google OAuth credentials
- Paystack account

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd securepay-wallet
```

2. **Create and activate virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

Required environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT secret key
- `GOOGLE_CLIENT_ID`: Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret
- `GOOGLE_REDIRECT_URI`: OAuth callback URL
- `PAYSTACK_SECRET_KEY`: Paystack secret key
- `PAYSTACK_PUBLIC_KEY`: Paystack public key
- `PAYSTACK_WEBHOOK_SECRET`: Paystack webhook secret
- `FRONTEND_URL`: Frontend application URL

5. **Create database tables**
```bash
# Using Alembic migrations
alembic upgrade head

# Or create tables directly
python -c "from database import engine, Base; import models; Base.metadata.create_all(bind=engine)"
```

6. **Run the application**
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### Authentication
- `GET /auth/google` - Redirect to Google OAuth
- `GET /auth/google/callback` - Google OAuth callback
- `GET /auth/me` - Get current user info

### API Keys
- `POST /keys/create` - Create a new API key
- `GET /keys/` - List all API keys
- `POST /keys/rollover` - Rollover expired API key
- `DELETE /keys/{key_id}` - Delete API key

### Wallet Operations
- `GET /wallet/` - Get wallet information
- `GET /wallet/balance` - Get wallet balance
- `POST /wallet/deposit` - Initialize deposit
- `GET /wallet/deposit/{reference}/status` - Check deposit status
- `POST /wallet/transfer` - Transfer funds
- `GET /wallet/transactions` - Get transaction history

### Webhooks
- `POST /webhook/paystack` - Paystack webhook endpoint

## Authentication Methods

### 1. JWT Token (for users)
```bash
# Login via Google OAuth, then use the token
curl -H "Authorization: Bearer <your-jwt-token>" \
  http://localhost:8000/wallet/balance
```

### 2. API Key (for services)
```bash
# Use API key in header
curl -H "x-api-key: <your-api-key>" \
  http://localhost:8000/wallet/balance
```

## API Key Permissions

- `read` - View wallet balance and transactions
- `deposit` - Initialize deposits
- `transfer` - Transfer funds between wallets

## Usage Examples

### Create an API Key
```bash
curl -X POST http://localhost:8000/keys/create \
  -H "Authorization: Bearer <jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Service Key",
    "permissions": ["read", "deposit"],
    "expiry": "30D"
  }'
```

### Deposit Funds
```bash
curl -X POST http://localhost:8000/wallet/deposit \
  -H "Authorization: Bearer <jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 1000.00
  }'
```

### Transfer Funds
```bash
curl -X POST http://localhost:8000/wallet/transfer \
  -H "x-api-key: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "recipient_wallet_number": "1234567890",
    "amount": 500.00,
    "description": "Payment for services"
  }'
```

## Webhook Configuration

Configure Paystack webhook in your Paystack dashboard:
- Webhook URL: `https://your-domain.com/webhook/paystack`
- Events: `charge.success`

The webhook endpoint will:
1. Verify the signature
2. Check for duplicate processing
3. Credit the wallet atomically
4. Update transaction status

## Database Schema

### Users
- Stores Google OAuth user information
- One-to-one relationship with Wallet

### Wallets
- Each user has one wallet
- Unique 10-digit wallet number
- Tracks balance

### Transactions
- Records all wallet activities
- Types: deposit, transfer_in, transfer_out
- Statuses: pending, success, failed

### API Keys
- Up to 5 active keys per user
- Hashed for security
- Granular permissions and expiration

## Security Best Practices

1. **Never expose your API keys** - They are shown only once during creation
2. **Use environment variables** - Never commit `.env` file
3. **Enable rate limiting** - Protect against abuse
4. **Verify webhook signatures** - Ensure requests come from Paystack
5. **Use HTTPS in production** - Encrypt data in transit
6. **Regular key rotation** - Use the rollover feature for expired keys

## Development

### Running Tests
```bash
pytest
```

### Database Migrations
```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Production Deployment

1. Set up a PostgreSQL database
2. Configure environment variables
3. Run database migrations
4. Use a production WSGI server (e.g., Gunicorn with Uvicorn workers)
```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```
5. Set up reverse proxy (Nginx/Apache)
6. Configure SSL certificate
7. Set up monitoring and logging

## 📚 Documentation

Comprehensive guides are available in the [`docs/`](./docs) directory:

- **[DEPLOYMENT.md](./docs/DEPLOYMENT.md)** - Complete production deployment guide with CI/CD setup
- **[TESTING.md](./docs/TESTING.md)** - Testing strategy, running tests, and writing new tests
- **[WEBHOOK_GUIDE.md](./docs/WEBHOOK_GUIDE.md)** - Paystack webhook integration and troubleshooting
- **[SECURITY.md](./docs/SECURITY.md)** - Security best practices and JWT handling
- **[TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md)** - Common issues and their solutions
- **[STRUCTURE.md](./docs/STRUCTURE.md)** - Project organization and conventions
- **[PENDING_TRANSACTIONS.md](./docs/PENDING_TRANSACTIONS.md)** - Managing pending transactions

## 🧪 Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-asyncio httpx

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific categories
pytest tests/unit           # Fast unit tests
pytest tests/integration    # API endpoint tests
pytest tests/e2e            # End-to-end workflows
```

See [docs/TESTING.md](./docs/TESTING.md) for detailed testing guide.

## 📚 Documentation

Comprehensive guides in the `docs/` directory:

- **[DEPLOYMENT.md](./docs/DEPLOYMENT.md)** - Production deployment with CI/CD
- **[TESTING.md](./docs/TESTING.md)** - Running and writing tests
- **[WEBHOOK_GUIDE.md](./docs/WEBHOOK_GUIDE.md)** - Paystack webhook integration
- **[PAYMENT_CALLBACK.md](./docs/PAYMENT_CALLBACK.md)** - Payment callback handling
- **[GITHUB_SECRETS.md](./docs/GITHUB_SECRETS.md)** - CI/CD secrets configuration
- **[SECURITY.md](./docs/SECURITY.md)** - Security best practices
- **[TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md)** - Common issues & solutions
- **[QUICK_REFERENCE.md](./docs/QUICK_REFERENCE.md)** - Quick command reference

## 🚀 Deployment

### Quick Deploy to Production

```bash
# 1. Initial server setup (run once)
curl -O https://raw.githubusercontent.com/yourusername/securepay-wallet/main/scripts/setup_server.sh
sudo bash setup_server.sh

# 2. Configure environment
sudo nano /opt/securepay-wallet/.env

# 3. Deploy application
sudo -u securepay bash /opt/securepay-wallet/scripts/deploy.sh
```

### Automated CI/CD (with uv ⚡)

The pipeline uses `uv` for 10-100x faster dependency installation.

Push to `main` branch triggers automatic:
- ✅ Testing (unit, integration, security)
- ✅ Code quality checks (Black, isort, Flake8)
- ✅ Security scans (Safety, Bandit)
- ✅ Deployment to production
- ✅ Database migrations
- ✅ Health checks
- ✅ Rollback on failure

**Setup**: Configure 4 GitHub secrets (see [docs/GITHUB_SECRETS.md](./docs/GITHUB_SECRETS.md))
- `SSH_PRIVATE_KEY` - SSH key for server access
- `SERVER_HOST` - Production server hostname
- `SERVER_USER` - SSH username
- `DEPLOY_PATH` - Application directory path

**See [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) for complete guide.**

## 🔧 Development

### Project Setup

```bash
# Clone and setup
git clone https://github.com/yourusername/securepay-wallet.git
cd securepay-wallet
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your credentials

# Run database migrations
alembic upgrade head

# Start development server
uvicorn main:app --reload
```

### Running E2E Tests

```bash
# Start server
uvicorn main:app --reload

# In another terminal, run E2E tests
python tests/e2e/test_full_workflow.py
```

## License

MIT License - see LICENSE file for details

## Support

For issues and questions, please open an issue on GitHub.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

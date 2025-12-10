# 🧪 Testing Guide

## Test Structure

```
tests/
├── __init__.py           # Test package init
├── conftest.py           # Shared fixtures and test configuration
├── unit/                 # Unit tests (fast, isolated)
│   ├── test_auth.py      # Authentication functions
│   ├── test_models.py    # Database models
│   └── test_paystack.py  # Paystack service
├── integration/          # Integration tests (API endpoints)
│   └── test_wallet_api.py
└── e2e/                  # End-to-end tests (full workflows)
    ├── test_api.py
    └── test_full_workflow.py
```

## Running Tests

### Install Test Dependencies

```bash
pip install pytest pytest-cov pytest-asyncio httpx
```

### Run All Tests

```bash
# Run everything
pytest

# With coverage report
pytest --cov=. --cov-report=html

# Verbose output
pytest -v
```

### Run Specific Test Categories

```bash
# Unit tests only (fast)
pytest tests/unit

# Integration tests
pytest tests/integration

# E2E tests
pytest tests/e2e

# Specific test file
pytest tests/unit/test_auth.py

# Specific test function
pytest tests/unit/test_auth.py::TestPasswordHashing::test_hash_api_key
```

### Run with Markers

```bash
# Run only fast tests
pytest -m fast

# Skip slow tests
pytest -m "not slow"
```

## Test Coverage

### Generate Coverage Report

```bash
# Terminal report
pytest --cov=. --cov-report=term

# HTML report (opens in browser)
pytest --cov=. --cov-report=html
open htmlcov/index.html

# XML report (for CI/CD)
pytest --cov=. --cov-report=xml
```

### Current Coverage Goals

- **Unit Tests**: > 80% coverage
- **Integration Tests**: Cover all API endpoints
- **E2E Tests**: Cover critical user flows

## Writing Tests

### Test Naming Convention

```python
# Good
def test_create_wallet_success():
    ...

def test_transfer_insufficient_funds():
    ...

# Bad
def test1():
    ...

def wallet_test():
    ...
```

### Using Fixtures

```python
import pytest

def test_get_balance(client, auth_headers, sample_wallet):
    """Test getting wallet balance"""
    response = client.get("/wallet/balance", headers=auth_headers)
    assert response.status_code == 200
```

### Available Fixtures

From `conftest.py`:

- `db_session` - Fresh database session
- `client` - FastAPI test client
- `sample_user` - Test user object
- `sample_wallet` - Test wallet with balance
- `auth_token` - Valid JWT token
- `auth_headers` - Authorization headers
- `sample_api_key` - Test API key

### Testing API Endpoints

```python
def test_endpoint(client, auth_headers):
    # Make request
    response = client.post(
        "/wallet/deposit",
        headers=auth_headers,
        json={"amount": 100.00}
    )
    
    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == 100.00
```

### Testing Authentication

```python
def test_protected_endpoint_without_auth(client):
    """Test that protected endpoint requires authentication"""
    response = client.get("/wallet/")
    assert response.status_code == 401
```

### Testing Database Models

```python
def test_wallet_creation(db_session, sample_user):
    """Test creating a wallet"""
    wallet = models.Wallet(
        user_id=sample_user.id,
        wallet_number="WAL0000000001",
        balance=0.00
    )
    db_session.add(wallet)
    db_session.commit()
    
    assert wallet.id is not None
```

### Mocking External Services

```python
from unittest.mock import Mock, patch

@patch('services.paystack.requests.post')
def test_paystack_initialize(mock_post):
    """Test Paystack transaction initialization"""
    # Mock response
    mock_response = Mock()
    mock_response.json.return_value = {
        "status": True,
        "data": {"authorization_url": "https://test.url"}
    }
    mock_post.return_value = mock_response
    
    # Test your code
    service = PaystackService()
    result = service.initialize_transaction(...)
    
    assert result["authorization_url"] == "https://test.url"
```

## Test Data

### Test Cards (Paystack)

```python
# Success
card_number = "4084084084084081"
cvv = "408"
pin = "0000"
otp = "123456"

# Insufficient funds
card_number = "4084080000000409"

# Declined
card_number = "4084082000000406"
```

### Test Environment Variables

Create `.env.test`:

```bash
DATABASE_URL=sqlite:///./test.db
SECRET_KEY=test-secret-key-for-testing
GOOGLE_CLIENT_ID=test-client-id
GOOGLE_CLIENT_SECRET=test-client-secret
PAYSTACK_SECRET_KEY=sk_test_your_test_key
PAYSTACK_WEBHOOK_SECRET=test-webhook-secret
FRONTEND_URL=http://localhost:3000
```

## Continuous Integration

Tests run automatically on:

- Every push to `main` or `develop`
- Every pull request
- Before deployment

See `.github/workflows/ci-cd.yml` for configuration.

## Troubleshooting Tests

### Database Connection Issues

```bash
# Use in-memory SQLite for tests
DATABASE_URL=sqlite:///:memory: pytest
```

### Import Errors

```bash
# Add project root to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

### Slow Tests

```bash
# Run in parallel (requires pytest-xdist)
pip install pytest-xdist
pytest -n auto
```

### Debug a Failing Test

```bash
# Show print statements
pytest -s

# Drop into debugger on failure
pytest --pdb

# Show local variables
pytest -l
```

## Best Practices

1. **Keep tests isolated** - Each test should be independent
2. **Use fixtures** - Avoid repetitive setup code
3. **Test edge cases** - Not just happy paths
4. **Mock external services** - Don't hit real APIs in tests
5. **Descriptive names** - Test names should explain what's being tested
6. **Assert clearly** - Use specific assertions, not just `assert result`
7. **Keep tests fast** - Unit tests should run in milliseconds
8. **Clean up** - Use fixtures with proper teardown

## Test Checklist

Before submitting code:

- [ ] All tests pass locally
- [ ] Added tests for new features
- [ ] Updated tests for changed behavior
- [ ] No skipped tests without good reason
- [ ] Coverage doesn't decrease
- [ ] Tests are well-named and documented

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [FastAPI testing guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [Testing best practices](https://docs.python-guide.org/writing/tests/)

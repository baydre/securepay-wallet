# Tests Directory

This directory contains all automated tests for SecurePay Wallet.

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-asyncio httpx

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific category
pytest tests/unit
pytest tests/integration
pytest tests/e2e
```

## Test Organization

### `unit/` - Unit Tests
Fast, isolated tests for individual functions and classes:
- `test_auth.py` - Authentication functions (JWT, API keys, hashing)
- `test_models.py` - Database models (Wallet, Transaction, APIKey)
- `test_paystack.py` - Paystack service (with mocked HTTP requests)

**Characteristics:**
- ⚡ Fast (< 1 second each)
- 🔒 Isolated (no external dependencies)
- 📊 High coverage target (> 80%)

### `integration/` - Integration Tests
Tests for API endpoints and database interactions:
- `test_wallet_api.py` - Wallet endpoints, transaction management, API key auth

**Characteristics:**
- 🔗 Tests multiple components together
- 🗄️ Uses test database
- 🌐 Tests full HTTP request/response cycle

### `e2e/` - End-to-End Tests
Complete user workflows from start to finish:
- `test_api.py` - Interactive API testing script
- `test_full_workflow.py` - Complete user flow (OAuth → API keys → Wallet ops)

**Characteristics:**
- 👤 Simulates real user interactions
- 🔄 Tests complete workflows
- 🧪 May require external services

## Test Fixtures

All shared test fixtures are defined in `conftest.py`:

```python
# Available fixtures:
- db_session         # Fresh database for each test
- client             # FastAPI test client
- sample_user        # Test user object
- sample_wallet      # Wallet with NGN 1000 balance
- auth_token         # Valid JWT token
- auth_headers       # Authorization headers
- sample_api_key     # Test API key with 'read' and 'deposit' permissions
```

## Writing New Tests

### Unit Test Example

```python
# tests/unit/test_new_feature.py
import pytest

def test_my_function():
    """Test description"""
    result = my_function("input")
    assert result == "expected_output"
```

### Integration Test Example

```python
# tests/integration/test_new_endpoint.py
def test_new_endpoint(client, auth_headers):
    """Test new API endpoint"""
    response = client.get("/new-endpoint", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["key"] == "value"
```

## Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=. --cov-report=html

# View report
open htmlcov/index.html
```

## Current Test Statistics

Run `pytest --cov=.` to see:
- Total lines of code
- Lines covered by tests
- Coverage percentage
- Missing lines

## Best Practices

1. ✅ **Test names should be descriptive**: `test_transfer_insufficient_funds()`
2. ✅ **One assertion per concept**: Don't test multiple things in one test
3. ✅ **Use fixtures**: Avoid repetitive setup code
4. ✅ **Test edge cases**: Not just happy paths
5. ✅ **Keep tests fast**: Unit tests should be milliseconds
6. ✅ **Mock external services**: Don't hit real APIs
7. ✅ **Clean up after tests**: Use fixtures with teardown

## CI/CD Integration

Tests run automatically on:
- Every push to `main` or `develop` branch
- Every pull request
- Before deployment

See `.github/workflows/ci-cd.yml` for CI configuration.

## Troubleshooting

### Tests failing locally but passing in CI

```bash
# Use same Python version as CI
pyenv install 3.11
pyenv local 3.11

# Clear pytest cache
pytest --cache-clear
```

### Database connection issues

```bash
# Tests use SQLite in-memory by default
# Check DATABASE_URL in test environment
echo $DATABASE_URL
```

### Import errors

```bash
# Add project root to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

## Documentation

See [docs/TESTING.md](../docs/TESTING.md) for comprehensive testing guide.

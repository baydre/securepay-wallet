# SecurePay Wallet - Root Cause Analysis & Fixes

## Problem Summary
API key creation and authentication were failing with multiple cascading issues.

## Root Causes Identified

### 1. **Bcrypt Version Incompatibility** ⚠️
**Error**: `ValueError: password cannot be longer than 72 bytes`

**Root Cause**:
- `passlib[bcrypt]` expected bcrypt < 4.0 with `__about__` module
- Installed bcrypt 5.0.0 removed `__about__` module
- passlib initialization failed trying to detect bcrypt version
- This happened even though our SHA256 hash was only 64 bytes (under 72-byte limit)

**Fix**: Replaced `passlib.CryptContext` with direct `bcrypt` library calls
```python
# Before (passlib - incompatible)
pwd_context = CryptContext(schemes=["bcrypt"])
hashed = pwd_context.hash(key)

# After (direct bcrypt - works!)
import bcrypt
salt = bcrypt.gensalt()
hashed = bcrypt.hashpw(sha256_hash.encode(), salt)
```

### 2. **Pydantic v1 vs v2 Validator Syntax** ⚠️
**Error**: `ValueError` during schema validation (silent failure in logs)

**Root Cause**:
- Using Pydantic 2.5.3 but with v1 `@validator` decorator syntax
- Pydantic v2 requires `@field_validator` with `@classmethod`

**Fix**: Updated all validators to Pydantic v2 syntax
```python
# Before (Pydantic v1)
@validator('permissions')
def validate_permissions(cls, v):
    ...

# After (Pydantic v2)
@field_validator('permissions')
@classmethod
def validate_permissions(cls, v):
    ...
```

### 3. **Timezone-Aware vs Naive Datetime Comparison** ⚠️
**Error**: `TypeError: can't compare offset-naive and offset-aware datetimes`

**Root Cause**:
- PostgreSQL stores timezone-aware datetimes (`2026-01-09 09:42:06+01:00`)
- Code used `datetime.utcnow()` which returns naive datetime
- Python cannot compare them directly

**Fix**: Added timezone handling in expiry check
```python
# Before
if api_key_record.expires_at < datetime.utcnow():

# After
from datetime import timezone
now = datetime.now(timezone.utc)
if api_key_record.expires_at.tzinfo is None:
    now = datetime.utcnow()
if expires_at < now:
```

### 4. **HTTPBearer Auto-Error Blocking API Keys** ⚠️
**Error**: `403 Forbidden` with `{"detail":"Not authenticated"}`

**Root Cause**:
- `HTTPBearer()` dependency has `auto_error=True` by default
- When no Bearer token present, FastAPI returns 403 BEFORE calling our function
- API key in header was never checked

**Fix**: Set `auto_error=False` to allow fallback to API key
```python
# Before (blocks API keys)
async def get_current_user_or_service(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    ...
)

# After (allows API keys)
async def get_current_user_or_service(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    ...
)
```

### 5. **Permission Mapping** ✓
**Issue**: Test used `wallet:read`, `wallet:write` but system expected `read`, `deposit`, `transfer`

**Fix**: Added permission mapping in validator
```python
permission_map = {
    "wallet:read": "read",
    "wallet:write": "deposit",
    "wallet:transfer": "transfer"
}
```

### 6. **API Endpoint Path** ✓
**Issue**: Endpoint at `/keys/create` but test called `/keys`

**Fix**: Added multiple route decorators
```python
@router.post("", ...)  # /keys
@router.post("/", ...)  # /keys/
@router.post("/create", ...)  # /keys/create
```

## Files Modified
1. `auth.py` - Replaced passlib with direct bcrypt
2. `schemas.py` - Updated all validators to Pydantic v2 syntax
3. `dependencies.py` - Fixed timezone comparison + HTTPBearer auto_error
4. `routers/keys_routes.py` - Added multiple route paths, updated expiry logic

## Test Results ✅
- API key creation: **WORKING**
- API key authentication: **WORKING**
- JWT authentication: **WORKING**
- Wallet balance with API key: **WORKING**
- Paystack deposit: **WORKING**
- Transaction history: **WORKING**

## Lessons Learned
1. Check library compatibility (passlib vs bcrypt versions)
2. When upgrading Pydantic, update all decorator syntax
3. Always handle timezone-aware vs naive datetimes
4. HTTPBearer auto_error blocks alternative auth methods
5. Deep debugging > trial and error when multiple issues cascade

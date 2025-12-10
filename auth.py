from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
import hashlib
from config import get_settings

settings = get_settings()


def hash_api_key(key: str) -> str:
    """
    Hash an API key using bcrypt directly
    
    We use SHA256 first to normalize the key length to 64 hex characters (32 bytes),
    which is well under bcrypt's 72-byte limit
    """
    # First, hash with SHA256 to get a fixed-length string
    sha256_hash = hashlib.sha256(key.encode()).hexdigest()
    # Then hash with bcrypt for secure storage
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(sha256_hash.encode(), salt)
    return hashed.decode('utf-8')  # Store as string in database


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against its hash
    
    First hash the plain key with SHA256, then verify with bcrypt
    """
    sha256_hash = hashlib.sha256(plain_key.encode()).hexdigest()
    return bcrypt.checkpw(sha256_hash.encode(), hashed_key.encode())


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    
    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    """Verify a JWT token and return the email"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        email: str = payload.get("sub")
        
        if email is None:
            return None
            
        return email
    except JWTError:
        return None


def parse_expiry_string(expiry: str) -> datetime:
    """
    Parse expiry string like '1H', '1D', '30M' to datetime
    H = hours, D = days, M = months (30 days)
    """
    amount = int(expiry[:-1])
    unit = expiry[-1].upper()
    
    if unit == 'H':
        delta = timedelta(hours=amount)
    elif unit == 'D':
        delta = timedelta(days=amount)
    elif unit == 'M':
        delta = timedelta(days=amount * 30)
    else:
        raise ValueError(f"Invalid expiry unit: {unit}. Use H, D, or M")
    
    return datetime.utcnow() + delta

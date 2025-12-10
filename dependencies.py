from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, Callable
from datetime import datetime
import models
from auth import verify_token, verify_api_key

security = HTTPBearer()


def get_db():
    """Get database session"""
    from database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> models.User:
    """
    Dependency to get the current authenticated user from JWT token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    email = verify_token(token)
    
    if email is None:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.email == email).first()
    
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_service(
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> models.User:
    """
    Dependency to get the current authenticated user from API key
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Find the API key in the database
    api_keys = db.query(models.APIKey).filter(models.APIKey.is_active == True).all()
    
    api_key_record = None
    for key in api_keys:
        if verify_api_key(x_api_key, key.hashed_key):
            api_key_record = key
            break
    
    if not api_key_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    # Check if the API key has expired
    from datetime import timezone
    now = datetime.now(timezone.utc)
    # Handle both timezone-aware and naive datetimes
    expires_at = api_key_record.expires_at
    if expires_at.tzinfo is None:
        # If stored datetime is naive, make current time naive too
        now = datetime.utcnow()
    
    if expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
        )
    
    # Get the associated user
    user = db.query(models.User).filter(models.User.id == api_key_record.user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    # Attach the API key permissions to the user for later checks
    user.api_permissions = api_key_record.permissions
    
    return user


def require_permission(permission: str) -> Callable:
    """
    Factory function to create a dependency that requires a specific permission
    Usage: Depends(require_permission("transfer"))
    """
    async def permission_checker(
        x_api_key: Optional[str] = Header(None),
        db: Session = Depends(get_db)
    ) -> models.User:
        user = await get_current_service(x_api_key, db)
        
        if not hasattr(user, 'api_permissions') or permission not in user.api_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' is required",
            )
        
        return user
    
    return permission_checker


async def get_current_user_or_service(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> models.User:
    """
    Dependency that accepts either JWT token or API key
    
    Set auto_error=False to allow API key fallback when no Bearer token is provided
    """
    # Try JWT first
    if credentials:
        try:
            return await get_current_user(credentials, db)
        except HTTPException:
            pass
    
    # Try API key
    if x_api_key:
        try:
            return await get_current_service(x_api_key, db)
        except HTTPException:
            pass
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Valid JWT token or API key is required",
    )

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import secrets
from datetime import datetime
import models
from schemas import APIKeyCreate, APIKeyResponse, APIKeyRolloverRequest, APIKeyRolloverResponse
from auth import hash_api_key, parse_expiry_string
from dependencies import get_db, get_current_user

router = APIRouter(prefix="/keys", tags=["API Keys"])


@router.post("", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
@router.post("/create", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new API key for the authenticated user
    
    - Maximum 5 active keys per user
    - Permissions: wallet:read, wallet:write, wallet:transfer
    - Expiry format: expires_in_days (integer for number of days)
    """
    # Check if user has reached the limit of 5 keys
    active_keys_count = db.query(models.APIKey).filter(
        models.APIKey.user_id == current_user.id,
        models.APIKey.is_active == True
    ).count()
    
    if active_keys_count >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum of 5 API keys allowed per user. Please delete or deactivate existing keys."
        )
    
    # Generate a secure API key
    plain_key = secrets.token_urlsafe(32)
    hashed_key = hash_api_key(plain_key)
    
    # Calculate expiry datetime
    from datetime import timedelta
    expires_at = datetime.utcnow() + timedelta(days=key_data.expires_in_days)
    
    # Create API key record
    api_key = models.APIKey(
        user_id=current_user.id,
        name=key_data.name,
        hashed_key=hashed_key,
        permissions=key_data.permissions,
        expires_at=expires_at,
        is_active=True
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    # Return the response with the plain key (only shown once)
    response = APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key=plain_key,  # Only returned on creation
        permissions=api_key.permissions,
        expires_at=api_key.expires_at,
        is_active=api_key.is_active,
        created_at=api_key.created_at
    )
    
    return response


@router.get("", response_model=List[APIKeyResponse])
@router.get("/", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all API keys for the authenticated user
    """
    api_keys = db.query(models.APIKey).filter(
        models.APIKey.user_id == current_user.id
    ).all()
    
    # Don't include the actual key in the list
    return [
        APIKeyResponse(
            id=key.id,
            name=key.name,
            permissions=key.permissions,
            expires_at=key.expires_at,
            is_active=key.is_active,
            created_at=key.created_at
        )
        for key in api_keys
    ]


@router.post("/rollover", response_model=APIKeyRolloverResponse)
async def rollover_api_key(
    rollover_data: APIKeyRolloverRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Rollover an expired API key
    
    - Creates a new key with the same permissions as the expired key
    - The old key must be expired and belong to the current user
    """
    # Find the expired key
    expired_key = db.query(models.APIKey).filter(
        models.APIKey.id == rollover_data.expired_key_id,
        models.APIKey.user_id == current_user.id
    ).first()
    
    if not expired_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Check if the key is actually expired
    if expired_key.expires_at > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only rollover expired keys"
        )
    
    # Check if user has reached the limit
    active_keys_count = db.query(models.APIKey).filter(
        models.APIKey.user_id == current_user.id,
        models.APIKey.is_active == True
    ).count()
    
    if active_keys_count >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum of 5 API keys allowed. Please delete existing keys."
        )
    
    # Generate a new API key with the same permissions
    plain_key = secrets.token_urlsafe(32)
    hashed_key = hash_api_key(plain_key)
    
    # Calculate new expiry (same duration as the original key)
    original_duration = expired_key.expires_at - expired_key.created_at
    new_expires_at = datetime.utcnow() + original_duration
    
    # Create new API key
    new_api_key = models.APIKey(
        user_id=current_user.id,
        name=f"{expired_key.name} (Rolled over)",
        hashed_key=hashed_key,
        permissions=expired_key.permissions,
        expires_at=new_expires_at,
        is_active=True
    )
    
    db.add(new_api_key)
    
    # Deactivate the old key
    expired_key.is_active = False
    
    db.commit()
    db.refresh(new_api_key)
    
    return APIKeyRolloverResponse(
        id=new_api_key.id,
        name=new_api_key.name,
        key=plain_key,
        permissions=new_api_key.permissions,
        expires_at=new_api_key.expires_at,
        message="API key rolled over successfully"
    )


@router.delete("/{key_id}", status_code=status.HTTP_200_OK)
async def delete_api_key(
    key_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete (deactivate) an API key
    """
    api_key = db.query(models.APIKey).filter(
        models.APIKey.id == key_id,
        models.APIKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Deactivate instead of delete for audit purposes
    api_key.is_active = False
    db.commit()
    
    return {"message": "API key deleted successfully"}

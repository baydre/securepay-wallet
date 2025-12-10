from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    google_id: str


class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Wallet Schemas
class WalletResponse(BaseModel):
    id: int
    wallet_number: str
    balance: float
    created_at: datetime
    
    class Config:
        from_attributes = True


class BalanceResponse(BaseModel):
    wallet_number: str
    balance: float


# Transaction Schemas
class DepositRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount must be greater than 0")
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        return round(v, 2)


class DepositResponse(BaseModel):
    authorization_url: str
    reference: str
    amount: float


class TransferRequest(BaseModel):
    recipient_wallet_number: str = Field(..., min_length=13, max_length=13, pattern=r"^WAL\d{10}$")
    amount: float = Field(..., gt=0)
    description: Optional[str] = None
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        return round(v, 2)


class TransferResponse(BaseModel):
    reference: str
    amount: float
    recipient_wallet_number: str
    status: str


class TransactionResponse(BaseModel):
    id: int
    type: str
    amount: float
    status: str
    reference: str
    description: Optional[str]
    recipient_wallet_number: Optional[str]
    sender_wallet_number: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# API Key Schemas
class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    permissions: List[str] = Field(..., min_items=1)
    expires_in_days: int = Field(default=30, ge=1, le=365, description="Number of days until key expires")
    
    @field_validator('permissions')
    @classmethod
    def validate_permissions(cls, v):
        # Map new-style permissions to old-style
        permission_map = {
            "wallet:read": "read",
            "wallet:write": "deposit",
            "wallet:transfer": "transfer"
        }
        
        allowed_permissions = {"wallet:read", "wallet:write", "wallet:transfer", "read", "deposit", "transfer"}
        normalized = []
        
        for perm in v:
            if perm not in allowed_permissions:
                raise ValueError(f'Invalid permission: {perm}. Allowed: {allowed_permissions}')
            # Normalize to old-style permission
            normalized.append(permission_map.get(perm, perm))
        
        return list(set(normalized))  # Remove duplicates


class APIKeyResponse(BaseModel):
    id: int
    name: str
    key: Optional[str] = None  # Only returned on creation
    permissions: List[str]
    expires_at: datetime
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class APIKeyRolloverRequest(BaseModel):
    expired_key_id: int


class APIKeyRolloverResponse(BaseModel):
    id: int
    name: str
    key: str
    permissions: List[str]
    expires_at: datetime
    message: str


# Authentication Schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


# Paystack Webhook Schema
class PaystackWebhookEvent(BaseModel):
    event: str
    data: dict

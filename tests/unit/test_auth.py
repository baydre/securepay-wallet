"""
Unit tests for authentication functions
"""
import pytest
from datetime import timedelta, datetime
import auth


class TestPasswordHashing:
    """Test password hashing functions"""
    
    def test_hash_api_key(self):
        """Test API key hashing"""
        key = "test_api_key_123"
        hashed = auth.hash_api_key(key)
        
        assert hashed is not None
        assert hashed != key  # Should be hashed
        assert len(hashed) > 0
    
    def test_verify_api_key_correct(self):
        """Test API key verification with correct key"""
        key = "test_api_key_123"
        hashed = auth.hash_api_key(key)
        
        assert auth.verify_api_key(key, hashed) is True
    
    def test_verify_api_key_incorrect(self):
        """Test API key verification with incorrect key"""
        key = "test_api_key_123"
        wrong_key = "wrong_api_key_456"
        hashed = auth.hash_api_key(key)
        
        assert auth.verify_api_key(wrong_key, hashed) is False
    
    def test_hash_consistency(self):
        """Test that same key produces different hashes (bcrypt salt)"""
        key = "test_api_key_123"
        hash1 = auth.hash_api_key(key)
        hash2 = auth.hash_api_key(key)
        
        # Hashes should be different due to random salt
        assert hash1 != hash2
        # But both should verify correctly
        assert auth.verify_api_key(key, hash1) is True
        assert auth.verify_api_key(key, hash2) is True


class TestJWTTokens:
    """Test JWT token creation and verification"""
    
    def test_create_access_token(self):
        """Test creating a JWT token"""
        data = {"sub": "test@example.com", "user_id": 1}
        token = auth.create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_access_token_with_expiry(self):
        """Test creating a JWT token with custom expiry"""
        data = {"sub": "test@example.com", "user_id": 1}
        expires_delta = timedelta(minutes=15)
        token = auth.create_access_token(data, expires_delta)
        
        assert token is not None
        assert isinstance(token, str)
    
    def test_verify_valid_token(self):
        """Test verifying a valid JWT token"""
        data = {"sub": "test@example.com"}
        token = auth.create_access_token(data)
        
        email = auth.verify_token(token)
        
        assert email is not None
        assert email == "test@example.com"
    
    def test_verify_invalid_token(self):
        """Test verifying an invalid JWT token"""
        invalid_token = "invalid.token.here"
        
        email = auth.verify_token(invalid_token)
        
        assert email is None
    
    def test_verify_expired_token(self):
        """Test verifying an expired JWT token"""
        data = {"sub": "test@example.com"}
        # Create token that expires immediately
        token = auth.create_access_token(data, timedelta(seconds=-1))
        
        email = auth.verify_token(token)
        
        assert email is None


class TestExpiryParsing:
    """Test expiry string parsing"""
    
    def test_parse_expiry_hours(self):
        """Test parsing hour expiry format"""
        result = auth.parse_expiry_string("24H")
        assert result > datetime.now()
    
    def test_parse_expiry_days(self):
        """Test parsing day expiry format"""
        result = auth.parse_expiry_string("7D")
        assert result > datetime.now()
    
    def test_parse_expiry_months(self):
        """Test parsing month expiry format"""
        result = auth.parse_expiry_string("1M")
        assert result > datetime.now()

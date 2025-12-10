"""
Unit tests for authentication functions
"""
import pytest
from datetime import timedelta
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
    
    def test_decode_valid_token(self):
        """Test decoding a valid JWT token"""
        data = {"sub": "test@example.com", "user_id": 1}
        token = auth.create_access_token(data)
        
        decoded = auth.decode_access_token(token)
        
        assert decoded is not None
        assert decoded["sub"] == "test@example.com"
        assert decoded["user_id"] == 1
        assert "exp" in decoded  # Should have expiry
    
    def test_decode_invalid_token(self):
        """Test decoding an invalid JWT token"""
        invalid_token = "invalid.token.here"
        
        decoded = auth.decode_access_token(invalid_token)
        
        assert decoded is None
    
    def test_decode_expired_token(self):
        """Test decoding an expired JWT token"""
        data = {"sub": "test@example.com", "user_id": 1}
        # Create token that expires immediately
        token = auth.create_access_token(data, timedelta(seconds=-1))
        
        decoded = auth.decode_access_token(token)
        
        assert decoded is None


class TestAPIKeyGeneration:
    """Test API key generation"""
    
    def test_generate_api_key_format(self):
        """Test that generated API keys have correct format"""
        key = auth.generate_api_key()
        
        assert key is not None
        assert isinstance(key, str)
        assert len(key) == 32  # Should be 32 characters
        assert key.startswith("sk_")  # Should have prefix
    
    def test_generate_api_key_uniqueness(self):
        """Test that generated API keys are unique"""
        keys = [auth.generate_api_key() for _ in range(10)]
        
        # All keys should be unique
        assert len(keys) == len(set(keys))

"""
Unit tests for wallet models
"""
import pytest
from datetime import datetime
import models


class TestWalletModel:
    """Test Wallet model"""
    
    def test_create_wallet(self, db_session, sample_user):
        """Test creating a wallet"""
        wallet = models.Wallet(
            user_id=sample_user.id,
            wallet_number="WAL0000000001",
            balance=0.00
        )
        db_session.add(wallet)
        db_session.commit()
        
        assert wallet.id is not None
        assert wallet.user_id == sample_user.id
        assert wallet.balance == 0.00
    
    def test_wallet_balance_update(self, db_session, sample_wallet):
        """Test updating wallet balance"""
        original_balance = sample_wallet.balance
        sample_wallet.balance += 500.00
        db_session.commit()
        
        db_session.refresh(sample_wallet)
        assert sample_wallet.balance == original_balance + 500.00
    
    def test_wallet_user_relationship(self, db_session, sample_wallet, sample_user):
        """Test wallet-user relationship"""
        assert sample_wallet.user.id == sample_user.id
        assert sample_wallet.user.email == sample_user.email


class TestTransactionModel:
    """Test Transaction model"""
    
    def test_create_transaction(self, db_session, sample_wallet):
        """Test creating a transaction"""
        transaction = models.Transaction(
            wallet_id=sample_wallet.id,
            type="deposit",
            amount=100.00,
            reference="TXN-TEST-001",
            status="pending"
        )
        db_session.add(transaction)
        db_session.commit()
        
        assert transaction.id is not None
        assert transaction.amount == 100.00
        assert transaction.status == "pending"
    
    def test_transaction_status_update(self, db_session, sample_wallet):
        """Test updating transaction status"""
        transaction = models.Transaction(
            wallet_id=sample_wallet.id,
            type="deposit",
            amount=100.00,
            reference="TXN-TEST-002",
            status="pending"
        )
        db_session.add(transaction)
        db_session.commit()
        
        transaction.status = "success"
        db_session.commit()
        
        db_session.refresh(transaction)
        assert transaction.status == "success"
    
    def test_transaction_wallet_relationship(self, db_session, sample_wallet):
        """Test transaction-wallet relationship"""
        transaction = models.Transaction(
            wallet_id=sample_wallet.id,
            type="deposit",
            amount=100.00,
            reference="TXN-TEST-003",
            status="pending"
        )
        db_session.add(transaction)
        db_session.commit()
        
        assert transaction.wallet.id == sample_wallet.id
        assert transaction.wallet.wallet_number == sample_wallet.wallet_number


class TestAPIKeyModel:
    """Test APIKey model"""
    
    def test_create_api_key(self, db_session, sample_user):
        """Test creating an API key"""
        from datetime import timedelta
        
        api_key = models.APIKey(
            user_id=sample_user.id,
            name="Test Key",
            key_hash="hashed_key_value",
            permissions=["read", "deposit"],
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add(api_key)
        db_session.commit()
        
        assert api_key.id is not None
        assert api_key.name == "Test Key"
        assert "read" in api_key.permissions
        assert "deposit" in api_key.permissions
    
    def test_api_key_expiry(self, db_session, sample_user):
        """Test API key expiry check"""
        from datetime import timedelta
        
        # Expired key
        expired_key = models.APIKey(
            user_id=sample_user.id,
            name="Expired Key",
            key_hash="hash1",
            permissions=["read"],
            expires_at=datetime.utcnow() - timedelta(days=1)
        )
        db_session.add(expired_key)
        
        # Valid key
        valid_key = models.APIKey(
            user_id=sample_user.id,
            name="Valid Key",
            key_hash="hash2",
            permissions=["read"],
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add(valid_key)
        db_session.commit()
        
        assert expired_key.expires_at < datetime.utcnow()
        assert valid_key.expires_at > datetime.utcnow()
    
    def test_api_key_user_relationship(self, db_session, sample_api_key, sample_user):
        """Test API key-user relationship"""
        assert sample_api_key.user.id == sample_user.id
        assert sample_api_key.user.email == sample_user.email

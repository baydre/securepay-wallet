"""
Integration tests for wallet API endpoints
"""
import pytest
from fastapi import status


class TestWalletEndpoints:
    """Test wallet-related API endpoints"""
    
    def test_get_wallet_authenticated(self, client, auth_headers, sample_wallet):
        """Test getting wallet with valid authentication"""
        response = client.get("/wallet/", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["wallet_number"] == sample_wallet.wallet_number
        assert "balance" in data
    
    def test_get_wallet_unauthenticated(self, client):
        """Test getting wallet without authentication"""
        response = client.get("/wallet/")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_balance_with_jwt(self, client, auth_headers, sample_wallet):
        """Test getting balance with JWT token"""
        response = client.get("/wallet/balance", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["balance"] == sample_wallet.balance
    
    def test_get_balance_with_api_key(self, client, sample_wallet, sample_api_key):
        """Test getting balance with API key"""
        headers = {"X-API-Key": sample_api_key.raw_key}
        response = client.get("/wallet/balance", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["balance"] == sample_wallet.balance


class TestTransactionEndpoints:
    """Test transaction-related API endpoints"""
    
    def test_get_transactions(self, client, auth_headers, sample_wallet, db_session):
        """Test getting transaction list"""
        import models
        
        # Create test transactions
        for i in range(3):
            tx = models.Transaction(
                wallet_id=sample_wallet.id,
                type="deposit",
                amount=100.00 * (i + 1),
                reference=f"TXN-TEST-{i}",
                status="success"
            )
            db_session.add(tx)
        db_session.commit()
        
        response = client.get("/wallet/transactions", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "transactions" in data
        assert len(data["transactions"]) == 3
    
    def test_get_pending_transactions(self, client, auth_headers, sample_wallet, db_session):
        """Test getting pending transactions"""
        import models
        
        # Create mixed status transactions
        statuses = ["pending", "success", "pending", "failed"]
        for i, stat in enumerate(statuses):
            tx = models.Transaction(
                wallet_id=sample_wallet.id,
                type="deposit",
                amount=100.00,
                reference=f"TXN-{stat}-{i}",
                status=stat
            )
            db_session.add(tx)
        db_session.commit()
        
        response = client.get("/wallet/transactions/pending", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["transactions"]) == 2  # Only pending ones
        for tx in data["transactions"]:
            assert tx["status"] == "pending"
    
    def test_get_transaction_summary(self, client, auth_headers, sample_wallet, db_session):
        """Test getting transaction summary statistics"""
        import models
        
        # Create test data
        test_data = [
            ("deposit", "success", 1000.00),
            ("deposit", "pending", 500.00),
            ("transfer", "success", 200.00),
            ("deposit", "failed", 300.00),
        ]
        
        for tx_type, tx_status, amount in test_data:
            tx = models.Transaction(
                wallet_id=sample_wallet.id,
                type=tx_type,
                amount=amount,
                reference=f"TXN-{tx_type}-{tx_status}",
                status=tx_status
            )
            db_session.add(tx)
        db_session.commit()
        
        response = client.get("/wallet/transactions/summary", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_transactions"] == 4
        assert "by_status" in data
        assert data["by_status"]["pending"]["count"] == 1
        assert data["by_status"]["success"]["count"] == 2


class TestAPIKeyEndpoints:
    """Test API key management endpoints"""
    
    def test_create_api_key(self, client, auth_headers, sample_user):
        """Test creating a new API key"""
        response = client.post(
            "/keys/create",
            headers=auth_headers,
            json={
                "name": "Test Key",
                "permissions": ["read", "deposit"],
                "expires_in_days": 30
            }
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "key" in data
        assert data["name"] == "Test Key"
        assert "read" in data["permissions"]
    
    def test_list_api_keys(self, client, auth_headers, sample_api_key):
        """Test listing user's API keys"""
        response = client.get("/keys/", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1
        # Keys should be masked
        for key in data:
            assert "key_hash" not in key or key.get("key_preview", "").endswith("***")
    
    def test_delete_api_key(self, client, auth_headers, sample_api_key, db_session):
        """Test deleting an API key"""
        response = client.delete(f"/keys/{sample_api_key.id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify it's deleted
        import models
        deleted_key = db_session.query(models.APIKey).filter(
            models.APIKey.id == sample_api_key.id
        ).first()
        assert deleted_key is None


class TestTransferEndpoints:
    """Test transfer functionality"""
    
    def test_transfer_success(self, client, auth_headers, sample_wallet, db_session):
        """Test successful wallet transfer"""
        import models
        
        # Create recipient user and wallet
        recipient = models.User(
            email="recipient@example.com",
            google_id="recipient_google_id",
            name="Recipient User"
        )
        db_session.add(recipient)
        db_session.commit()
        
        recipient_wallet = models.Wallet(
            user_id=recipient.id,
            wallet_number="WAL0000000002",
            balance=0.00
        )
        db_session.add(recipient_wallet)
        db_session.commit()
        
        # Perform transfer
        response = client.post(
            "/wallet/transfer",
            headers=auth_headers,
            json={
                "recipient_wallet_number": "WAL0000000002",
                "amount": 100.00,
                "description": "Test transfer"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["amount"] == 100.00
        assert data["status"] == "success"
    
    def test_transfer_insufficient_funds(self, client, auth_headers, sample_wallet, db_session):
        """Test transfer with insufficient funds"""
        import models
        
        # Create recipient
        recipient = models.User(
            email="recipient2@example.com",
            google_id="recipient2_google_id",
            name="Recipient User 2"
        )
        db_session.add(recipient)
        db_session.commit()
        
        recipient_wallet = models.Wallet(
            user_id=recipient.id,
            wallet_number="WAL0000000003",
            balance=0.00
        )
        db_session.add(recipient_wallet)
        db_session.commit()
        
        # Try to transfer more than balance
        excessive_amount = sample_wallet.balance + 1000.00
        response = client.post(
            "/wallet/transfer",
            headers=auth_headers,
            json={
                "recipient_wallet_number": "WAL0000000003",
                "amount": excessive_amount,
                "description": "Test transfer"
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "insufficient" in response.json()["detail"].lower()

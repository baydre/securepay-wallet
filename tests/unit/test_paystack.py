"""
Unit tests for Paystack service
"""
import pytest
from unittest.mock import Mock, patch
from services.paystack import PaystackService
import hmac
import hashlib


class TestPaystackService:
    """Test Paystack service methods"""
    
    @patch('services.paystack.requests.post')
    def test_initialize_transaction_success(self, mock_post):
        """Test successful transaction initialization"""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": True,
            "data": {
                "authorization_url": "https://checkout.paystack.com/test",
                "access_code": "test_access_code",
                "reference": "TXN-TEST-001"
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        service = PaystackService()
        result = service.initialize_transaction(
            email="test@example.com",
            amount=1000.00,
            reference="TXN-TEST-001"
        )
        
        assert result["authorization_url"] == "https://checkout.paystack.com/test"
        assert result["access_code"] == "test_access_code"
        
        # Verify the API was called with correct parameters
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs['json']['amount'] == 100000  # 1000 * 100 kobo
        assert call_kwargs['json']['email'] == "test@example.com"
    
    @patch('services.paystack.requests.post')
    def test_initialize_transaction_failure(self, mock_post):
        """Test failed transaction initialization"""
        # Mock failed response
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": False,
            "message": "Invalid email address"
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        service = PaystackService()
        
        with pytest.raises(Exception) as exc_info:
            service.initialize_transaction(
                email="invalid-email",
                amount=1000.00,
                reference="TXN-TEST-002"
            )
        
        assert "Invalid email address" in str(exc_info.value)
    
    @patch('services.paystack.requests.get')
    def test_verify_transaction_success(self, mock_get):
        """Test successful transaction verification"""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": True,
            "data": {
                "reference": "TXN-TEST-003",
                "amount": 100000,
                "status": "success"
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        service = PaystackService()
        result = service.verify_transaction("TXN-TEST-003")
        
        assert result["reference"] == "TXN-TEST-003"
        assert result["amount"] == 100000
        assert result["status"] == "success"
    
    def test_verify_webhook_signature_valid(self):
        """Test valid webhook signature verification"""
        payload = b'{"event": "charge.success", "data": {}}'
        secret = "test_webhook_secret"
        
        # Create valid signature
        signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()
        
        # Mock settings
        with patch('services.paystack.settings') as mock_settings:
            mock_settings.paystack_webhook_secret = secret
            
            result = PaystackService.verify_webhook_signature(payload, signature)
            assert result is True
    
    def test_verify_webhook_signature_invalid(self):
        """Test invalid webhook signature verification"""
        payload = b'{"event": "charge.success", "data": {}}'
        secret = "test_webhook_secret"
        invalid_signature = "invalid_signature_here"
        
        # Mock settings
        with patch('services.paystack.settings') as mock_settings:
            mock_settings.paystack_webhook_secret = secret
            
            result = PaystackService.verify_webhook_signature(payload, invalid_signature)
            assert result is False


class TestPaystackAmountConversion:
    """Test Paystack amount conversion (NGN to kobo)"""
    
    @patch('services.paystack.requests.post')
    def test_amount_conversion_to_kobo(self, mock_post):
        """Test that amounts are correctly converted to kobo"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": True,
            "data": {"authorization_url": "test", "access_code": "test"}
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        service = PaystackService()
        
        # Test various amounts
        test_cases = [
            (100.00, 10000),     # NGN 100 = 10,000 kobo
            (1000.00, 100000),   # NGN 1,000 = 100,000 kobo
            (0.50, 50),          # NGN 0.50 = 50 kobo
            (2500.75, 250075),   # NGN 2,500.75 = 250,075 kobo
        ]
        
        for naira, expected_kobo in test_cases:
            service.initialize_transaction(
                email="test@example.com",
                amount=naira,
                reference=f"TXN-{naira}"
            )
            
            # Get the last call's kwargs
            call_kwargs = mock_post.call_args[1]
            assert call_kwargs['json']['amount'] == expected_kobo

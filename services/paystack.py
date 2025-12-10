import requests
from typing import Dict, Optional
from config import get_settings

settings = get_settings()


class PaystackService:
    """Service for interacting with Paystack API"""
    
    BASE_URL = "https://api.paystack.co"
    
    def __init__(self):
        self.secret_key = settings.paystack_secret_key
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
    
    def initialize_transaction(self, email: str, amount: float, reference: str) -> Dict:
        """
        Initialize a Paystack transaction
        
        Args:
            email: Customer's email
            amount: Amount in kobo (multiply by 100)
            reference: Unique transaction reference
        
        Returns:
            Dict containing authorization_url and access_code
        """
        url = f"{self.BASE_URL}/transaction/initialize"
        
        # Convert amount to kobo (Paystack uses kobo)
        amount_in_kobo = int(amount * 100)
        
        # Use API status check endpoint as callback if no frontend URL configured
        # This allows testing without a frontend application
        callback_url = f"{settings.frontend_url}/wallet/deposit/callback"
        if not settings.frontend_url or settings.frontend_url.startswith("http://localhost:3000"):
            # For backend-only testing, redirect to our status check page
            # Use BACKEND_URL from settings, or construct from request if available
            backend_url = getattr(settings, 'backend_url', 'http://localhost:8000')
            callback_url = f"{backend_url}/wallet/deposit/{reference}/status"
        
        payload = {
            "email": email,
            "amount": amount_in_kobo,
            "reference": reference,
            "callback_url": callback_url
        }
        
        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get("status"):
            raise Exception(f"Paystack error: {data.get('message')}")
        
        return data["data"]
    
    def verify_transaction(self, reference: str) -> Dict:
        """
        Verify a Paystack transaction
        
        Args:
            reference: Transaction reference to verify
        
        Returns:
            Dict containing transaction details
        """
        url = f"{self.BASE_URL}/transaction/verify/{reference}"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get("status"):
            raise Exception(f"Paystack error: {data.get('message')}")
        
        return data["data"]
    
    @staticmethod
    def verify_webhook_signature(payload: bytes, signature: str) -> bool:
        """
        Verify Paystack webhook signature
        
        Args:
            payload: Raw request body as bytes
            signature: X-Paystack-Signature header value
        
        Returns:
            Boolean indicating if signature is valid
        """
        import hmac
        import hashlib
        
        expected_signature = hmac.new(
            settings.paystack_webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)

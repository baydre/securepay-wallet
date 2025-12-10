#!/usr/bin/env python3
"""
Test script for SecurePay Wallet API
Tests Google OAuth and Paystack integration
"""
import requests
import json
from time import sleep

BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test if the API is running"""
    print("\n🏥 Testing Health Check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API is healthy!")
            print(f"   App: {data['app']}")
            print(f"   Version: {data['version']}")
            print(f"   Database: {data['database']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_google_oauth_redirect():
    """Test Google OAuth redirect"""
    print("\n🔐 Testing Google OAuth Redirect...")
    try:
        response = requests.get(f"{BASE_URL}/auth/google", allow_redirects=False)
        if response.status_code in [302, 307]:
            print(f"✅ OAuth redirect working!")
            print(f"   Redirect URL: {response.headers.get('Location', 'N/A')[:80]}...")
            print(f"\n   📝 To complete OAuth flow:")
            print(f"   1. Open in browser: {BASE_URL}/auth/google")
            print(f"   2. Sign in with Google")
            print(f"   3. You'll be redirected with a JWT token")
            return True
        else:
            print(f"❌ OAuth redirect failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_with_jwt(jwt_token):
    """Test API endpoints with JWT token"""
    print(f"\n🔑 Testing with JWT Token...")
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    
    # Test get wallet
    print("\n   📊 Testing Get Wallet...")
    try:
        response = requests.get(f"{BASE_URL}/wallet/", headers=headers)
        if response.status_code == 200:
            wallet = response.json()
            print(f"   ✅ Wallet retrieved!")
            print(f"      Wallet Number: {wallet['wallet_number']}")
            print(f"      Balance: ₦{wallet['balance']}")
            return wallet
        else:
            print(f"   ❌ Failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def test_deposit(jwt_token, amount=1000.00):
    """Test deposit initialization with Paystack"""
    print(f"\n💰 Testing Deposit (₦{amount})...")
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/wallet/deposit",
            headers=headers,
            json={"amount": amount}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Deposit initialized!")
            print(f"   Reference: {data['reference']}")
            print(f"   Amount: ₦{data['amount']}")
            print(f"\n   🌐 Payment URL:")
            print(f"   {data['authorization_url']}")
            print(f"\n   📝 To complete payment:")
            print(f"   1. Open the URL above in your browser")
            print(f"   2. Use test card: 4084084084084081")
            print(f"   3. Expiry: Any future date")
            print(f"   4. CVV: 123")
            print(f"   5. OTP: 123456")
            return data
        else:
            print(f"❌ Deposit failed: {response.status_code}")
            print(f"   {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_api_key_creation(jwt_token):
    """Test API key creation"""
    print(f"\n🔐 Testing API Key Creation...")
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/keys/create",
            headers=headers,
            json={
                "name": "Test API Key",
                "permissions": ["read", "deposit"],
                "expiry": "30D"
            }
        )
        
        if response.status_code == 201:
            data = response.json()
            print(f"✅ API Key created!")
            print(f"   Name: {data['name']}")
            print(f"   Key: {data['key'][:20]}... (save this!)")
            print(f"   Permissions: {', '.join(data['permissions'])}")
            print(f"   Expires: {data['expires_at']}")
            return data
        else:
            print(f"❌ API Key creation failed: {response.status_code}")
            print(f"   {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_with_api_key(api_key):
    """Test endpoints with API key"""
    print(f"\n🔑 Testing with API Key...")
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    # Test get balance
    print("\n   📊 Testing Get Balance with API Key...")
    try:
        response = requests.get(f"{BASE_URL}/wallet/balance", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Balance retrieved!")
            print(f"      Wallet Number: {data['wallet_number']}")
            print(f"      Balance: ₦{data['balance']}")
            return True
        else:
            print(f"   ❌ Failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def interactive_test():
    """Interactive testing menu"""
    print("="*60)
    print("🚀 SecurePay Wallet API Test Suite")
    print("="*60)
    
    # Run health check
    if not test_health_check():
        print("\n❌ API is not running. Please start it with:")
        print("   uvicorn main:app --reload")
        return
    
    # Test OAuth redirect
    test_google_oauth_redirect()
    
    print("\n" + "="*60)
    print("📋 Manual Testing Steps:")
    print("="*60)
    
    print("\n1️⃣  First, authenticate via Google OAuth:")
    print(f"    Open: {BASE_URL}/auth/google")
    print("    After login, copy the JWT token from the redirect URL")
    
    jwt_token = input("\n    Paste your JWT token here (or press Enter to skip): ").strip()
    
    if jwt_token:
        # Test with JWT
        wallet = test_with_jwt(jwt_token)
        
        if wallet:
            # Test deposit
            test_deposit(jwt_token, 1000.00)
            
            # Test API key creation
            api_key_data = test_api_key_creation(jwt_token)
            
            if api_key_data:
                # Test with API key
                test_with_api_key(api_key_data['key'])
    
    print("\n" + "="*60)
    print("✅ Testing Complete!")
    print("="*60)
    print("\n📚 API Documentation: http://localhost:8000/docs")
    print("🔗 Alternative Docs: http://localhost:8000/redoc")


if __name__ == "__main__":
    interactive_test()

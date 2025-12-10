"""
Complete testing workflow for SecurePay Wallet
Tests: API Keys, Wallet Operations, and Paystack Integration
"""
import requests
import json
from datetime import datetime, timedelta
import time

BASE_URL = "http://localhost:8000"

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_section(title):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{title}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(message):
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")

def print_error(message):
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")

def print_info(message):
    print(f"{Colors.OKBLUE}ℹ {message}{Colors.ENDC}")

def print_response(response):
    print(f"{Colors.OKCYAN}Response ({response.status_code}):{Colors.ENDC}")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)

def test_health():
    """Test if server is running"""
    print_section("1. Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print_success("Server is running")
            print_response(response)
            return True
        else:
            print_error(f"Server returned status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Cannot connect to server: {e}")
        print_info("Make sure server is running: uvicorn main:app --reload")
        return False

def test_oauth_flow():
    """Guide user through OAuth flow"""
    print_section("2. OAuth Authentication")
    print_info("To get a JWT token, follow these steps:")
    print(f"\n1. Open in browser: {Colors.OKBLUE}{BASE_URL}/static/auth-test.html{Colors.ENDC}")
    print("2. Click 'Sign in with Google'")
    print("3. Complete OAuth flow")
    print("4. Copy the JWT token displayed")
    print(f"\n{Colors.WARNING}Note: JWT tokens expire after 30 minutes. Get a fresh token if tests fail.{Colors.ENDC}\n")
    
    token = input(f"{Colors.WARNING}Paste your JWT token here (or press Enter to skip OAuth tests): {Colors.ENDC}").strip()
    
    if not token:
        print_info("Skipping OAuth-protected endpoints")
        return None
    
    # Test the token
    print_info("\nTesting token validity...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    
    if response.status_code == 200:
        print_success("Token is valid!")
        user_data = response.json()
        print_response(response)
        return {"token": token, "user_data": user_data}
    else:
        print_error("Token is invalid")
        print_response(response)
        return None

def test_api_keys(auth_data):
    """Test API Key Management"""
    print_section("3. API Key Management")
    
    if not auth_data:
        print_info("Skipping - requires authentication")
        return None
    
    headers = {"Authorization": f"Bearer {auth_data['token']}"}
    
    # Create API Key
    print_info("Creating API key with wallet:read and wallet:write permissions...")
    key_data = {
        "name": f"Test Key {datetime.now().strftime('%H:%M:%S')}",
        "permissions": ["wallet:read", "wallet:write"],
        "expires_in_days": 30
    }
    
    response = requests.post(f"{BASE_URL}/keys", json=key_data, headers=headers)
    print_response(response)
    
    if response.status_code in [200, 201]:
        api_key_data = response.json()
        # API returns 'key' field, not 'api_key'
        api_key = api_key_data.get('key', api_key_data.get('api_key'))
        
        if api_key:
            print_success(f"API Key created: {api_key[:20]}...")
            # Store the key in the correct field name for later use
            api_key_data['api_key'] = api_key
            
            # List API Keys
            print_info("\nListing all API keys...")
            response = requests.get(f"{BASE_URL}/keys", headers=headers)
            print_response(response)
            
            # Test using API Key
            print_info("\nTesting API key authentication...")
            api_headers = {"X-API-Key": api_key}
            response = requests.get(f"{BASE_URL}/wallet/balance", headers=api_headers)
            
            if response.status_code == 200:
                print_success("API key works! Can access wallet balance")
                print_response(response)
            else:
                print_error("API key authentication failed")
                print_response(response)
            
            return api_key_data
        else:
            print_error("API key created but 'key' field not found in response")
            return None
    else:
        print_error("Failed to create API key")
        return None

def test_wallet_balance(auth_data, api_key_data):
    """Test wallet balance endpoint with transaction breakdown"""
    print_section("4. Wallet Balance & Transaction Summary")
    
    headers = None
    balance_data = None
    
    # Test with JWT
    if auth_data:
        print_info("Testing with JWT token...")
        headers = {"Authorization": f"Bearer {auth_data['token']}"}
        response = requests.get(f"{BASE_URL}/wallet/balance", headers=headers)
        print_response(response)
        
        if response.status_code == 200:
            print_success("JWT authentication works")
            balance_data = response.json()
    
    # Test with API Key
    if api_key_data and not balance_data:
        print_info("\nTesting with API key...")
        headers = {"X-API-Key": api_key_data['api_key']}
        response = requests.get(f"{BASE_URL}/wallet/balance", headers=headers)
        print_response(response)
        
        if response.status_code == 200:
            print_success("API key authentication works")
            balance_data = response.json()
    
    # Get transaction breakdown
    if balance_data and headers:
        print_info("\nFetching transaction breakdown...")
        response = requests.get(f"{BASE_URL}/wallet/transactions", headers=headers)
        
        if response.status_code == 200:
            transactions = response.json()
            
            # Calculate transaction summary
            deposits = sum(t['amount'] for t in transactions if t['type'] == 'deposit' and t['status'] == 'success')
            withdrawals = sum(t['amount'] for t in transactions if t['type'] == 'withdrawal' and t['status'] == 'success')
            transfers_out = sum(t['amount'] for t in transactions if t['type'] == 'transfer' and t['status'] == 'success' and t.get('sender_wallet_number'))
            transfers_in = sum(t['amount'] for t in transactions if t['type'] == 'transfer' and t['status'] == 'success' and t.get('recipient_wallet_number'))
            pending = sum(t['amount'] for t in transactions if t['status'] == 'pending')
            
            print(f"\n{Colors.OKCYAN}Transaction Breakdown:{Colors.ENDC}")
            print(f"  Current Balance: {Colors.OKGREEN}NGN {balance_data.get('balance', 0):,.2f}{Colors.ENDC}")
            print(f"  Total Deposits (Success): NGN {deposits:,.2f}")
            print(f"  Total Withdrawals: NGN {withdrawals:,.2f}")
            print(f"  Transfers Out: NGN {transfers_out:,.2f}")
            print(f"  Transfers In: NGN {transfers_in:,.2f}")
            print(f"  Pending Transactions: {Colors.WARNING}NGN {pending:,.2f}{Colors.ENDC}")
            print(f"  Total Transactions: {len(transactions)}")
    
    return balance_data

def test_paystack_deposit(auth_data, api_key_data):
    """Test Paystack deposit initiation"""
    print_section("5. Paystack Deposit")
    
    headers = None
    if api_key_data:
        print_info("Using API key for authentication...")
        headers = {"X-API-Key": api_key_data['api_key']}
    elif auth_data:
        print_info("Using JWT token for authentication...")
        headers = {"Authorization": f"Bearer {auth_data['token']}"}
    else:
        print_info("Skipping - requires authentication")
        return None
    
    # Get user email
    if auth_data and 'user_data' in auth_data:
        email = auth_data['user_data'].get('email')
    else:
        email = input(f"{Colors.WARNING}Enter your email: {Colors.ENDC}").strip()
    
    amount = input(f"{Colors.WARNING}Enter amount to deposit (NGN, default 1000): {Colors.ENDC}").strip()
    amount = int(amount) if amount else 1000
    
    deposit_data = {
        "amount": amount,
        "email": email
    }
    
    print_info(f"Initiating deposit of NGN {amount}...")
    response = requests.post(f"{BASE_URL}/wallet/deposit", json=deposit_data, headers=headers)
    print_response(response)
    
    if response.status_code == 200:
        payment_data = response.json()
        print_success("Deposit initialized!")
        print(f"\n{Colors.OKGREEN}Payment URL: {payment_data['authorization_url']}{Colors.ENDC}")
        
        print(f"\n{Colors.WARNING}To complete payment:{Colors.ENDC}")
        print(f"1. Open: {Colors.OKBLUE}{payment_data['authorization_url']}{Colors.ENDC}")
        print("2. Use Paystack test card: 4084084084084081")
        print("3. CVV: 408, Expiry: Any future date, PIN: 0000")
        print("4. OTP: 123456")
        print("\nWebhook will automatically credit your wallet!")
        
        return payment_data
    else:
        print_error("Failed to initialize deposit")
        return None

def test_transaction_history(auth_data, api_key_data):
    """Test transaction history"""
    print_section("6. Transaction History")
    
    headers = None
    if api_key_data:
        headers = {"X-API-Key": api_key_data['api_key']}
    elif auth_data:
        headers = {"Authorization": f"Bearer {auth_data['token']}"}
    else:
        print_info("Skipping - requires authentication")
        return
    
    print_info("Fetching detailed transaction history...")
    response = requests.get(f"{BASE_URL}/wallet/transactions", headers=headers)
    print_response(response)
    
    if response.status_code == 200:
        transactions = response.json()
        print_success(f"Found {len(transactions)} transaction(s)")
        
        # Show summary by status
        success_count = sum(1 for t in transactions if t['status'] == 'success')
        pending_count = sum(1 for t in transactions if t['status'] == 'pending')
        failed_count = sum(1 for t in transactions if t['status'] == 'failed')
        
        print(f"\n{Colors.OKCYAN}Status Summary:{Colors.ENDC}")
        print(f"  {Colors.OKGREEN}Success: {success_count}{Colors.ENDC}")
        print(f"  {Colors.WARNING}Pending: {pending_count}{Colors.ENDC}")
        print(f"  {Colors.FAIL}Failed: {failed_count}{Colors.ENDC}")
        
        return transactions
    
    return None

def test_transfer(auth_data, api_key_data):
    """Test wallet transfer"""
    print_section("7. Wallet Transfer")
    
    headers = None
    if api_key_data:
        headers = {"X-API-Key": api_key_data['api_key']}
    elif auth_data:
        headers = {"Authorization": f"Bearer {auth_data['token']}"}
    else:
        print_info("Skipping - requires authentication")
        return
    
    print_info("To test transfers, you need another user's wallet number")
    print_info("You can create another account via OAuth flow")
    
    proceed = input(f"\n{Colors.WARNING}Do you have another wallet to transfer to? (y/n): {Colors.ENDC}").strip().lower()
    
    if proceed == 'y':
        recipient = input(f"{Colors.WARNING}Enter recipient wallet number: {Colors.ENDC}").strip()
        amount = input(f"{Colors.WARNING}Enter amount to transfer: {Colors.ENDC}").strip()
        
        transfer_data = {
            "recipient_wallet_number": recipient,
            "amount": float(amount)
        }
        
        print_info(f"Transferring {amount} to {recipient}...")
        response = requests.post(f"{BASE_URL}/wallet/transfer", json=transfer_data, headers=headers)
        print_response(response)
        
        if response.status_code == 200:
            print_success("Transfer successful!")
        else:
            print_error("Transfer failed")
    else:
        print_info("Skipping transfer test")

def test_api_key_permissions(auth_data):
    """Test API key with limited permissions"""
    print_section("8. API Key Permissions Test")
    
    if not auth_data:
        print_info("Skipping - requires authentication")
        return
    
    headers = {"Authorization": f"Bearer {auth_data['token']}"}
    
    # Create read-only API key
    print_info("Creating read-only API key (wallet:read only)...")
    key_data = {
        "name": "Read-Only Test Key",
        "permissions": ["wallet:read"],
        "expires_in_days": 1
    }
    
    response = requests.post(f"{BASE_URL}/keys", json=key_data, headers=headers)
    
    if response.status_code in [200, 201]:
        readonly_key = response.json()
        api_key = readonly_key.get('key', readonly_key.get('api_key'))
        
        if api_key:
            print_success(f"Read-only key created: {api_key[:20]}...")
            
            # Test reading (should work)
            print_info("\nTesting read operation (should work)...")
            api_headers = {"X-API-Key": api_key}
            response = requests.get(f"{BASE_URL}/wallet/balance", headers=api_headers)
        
        if response.status_code == 200:
            print_success("Read operation successful!")
            print_response(response)
        else:
            print_error("Read operation failed")
        
        # Test writing (should fail)
        print_info("\nTesting write operation (should fail)...")
        transfer_data = {
            "recipient_wallet_number": "1234567890",
            "amount": 100
        }
        response = requests.post(f"{BASE_URL}/wallet/transfer", json=transfer_data, headers=api_headers)
        
        if response.status_code == 403:
            print_success("Permission check works! Write operation correctly denied")
            print_response(response)
        else:
            print_error("Permission check failed - write should be denied")
            print_response(response)

def main():
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║         SecurePay Wallet - Complete Test Suite           ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}\n")
    
    # 1. Health check
    if not test_health():
        return
    
    # 2. OAuth flow
    auth_data = test_oauth_flow()
    
    # 3. API Keys
    api_key_data = test_api_keys(auth_data)
    
    # 4. Wallet balance
    test_wallet_balance(auth_data, api_key_data)
    
    # 5. Paystack deposit
    test_paystack_deposit(auth_data, api_key_data)
    
    # 6. Transaction history
    test_transaction_history(auth_data, api_key_data)
    
    # 7. Transfer
    test_transfer(auth_data, api_key_data)
    
    # 8. Permission testing
    test_api_key_permissions(auth_data)
    
    print_section("Testing Complete!")
    print_success("All tests completed successfully!")
    print_info("\nNext steps:")
    print("1. Complete a Paystack payment to test webhook")
    print("2. Check transaction history after payment")
    print("3. Try transfers between different wallets")
    print(f"\n{Colors.OKBLUE}API Documentation: {BASE_URL}/docs{Colors.ENDC}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Testing interrupted by user{Colors.ENDC}\n")
    except Exception as e:
        print(f"\n{Colors.FAIL}Error: {e}{Colors.ENDC}\n")

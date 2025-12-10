# Postman Collection for SecurePay Wallet API

This directory would contain Postman collection files for testing the API.

## Quick Test Flow

1. **Authenticate**
   - Navigate to `/auth/google` in browser
   - Complete Google OAuth
   - Copy the JWT token from the callback URL

2. **Create API Key**
   - Use the JWT token to call `POST /keys/create`
   - Save the returned API key (shown only once!)

3. **Test Wallet Operations**
   - Get balance: `GET /wallet/balance`
   - Initialize deposit: `POST /wallet/deposit`
   - Transfer funds: `POST /wallet/transfer`
   - View transactions: `GET /wallet/transactions`

4. **Test with API Key**
   - Use `x-api-key` header instead of `Authorization: Bearer`
   - Test permissions (read, deposit, transfer)

## Environment Variables for Postman

- `base_url`: http://localhost:8000
- `jwt_token`: Your JWT token from OAuth
- `api_key`: Your generated API key
- `wallet_number`: Your wallet number

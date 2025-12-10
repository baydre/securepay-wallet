# How to Complete Pending Transactions

## Understanding Pending Transactions

Pending transactions are created when you initialize a Paystack deposit but haven't completed the payment yet. They show in your transaction history with `status: "pending"` and are NOT included in your wallet balance.

## View Your Pending Transactions

### Option 1: Using the API
```bash
# Get all pending transactions
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:8000/wallet/transactions/pending

# Or filter by status
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:8000/wallet/transactions?status=pending
```

### Option 2: Using the Test Script
The test workflow automatically shows pending amounts:
```bash
python3 test_full_workflow.py
```

## Complete a Pending Deposit

### Step 1: Get Transaction Reference
Find the reference from your pending transactions. Example: `TXN-20251210081957-KBODC6JN`

### Step 2: Check Status & Get Payment URL
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:8000/wallet/deposit/TXN-20251210081957-KBODC6JN/status
```

This returns the Paystack payment URL if still pending.

### Step 3: Complete Payment
1. **Open the authorization URL** from the deposit response
2. **Use Paystack Test Card:**
   - Card Number: `4084084084084081`
   - CVV: `408`
   - Expiry: Any future date (e.g., `12/26`)
   - PIN: `0000`
   - OTP: `123456`

### Step 4: Verify Completion
The webhook should automatically credit your wallet within seconds. Verify by:

```bash
# Check wallet balance
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:8000/wallet/balance

# View completed transactions
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:8000/wallet/transactions/completed

# Or check specific transaction status
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:8000/wallet/deposit/YOUR_REFERENCE/status
```

## New API Endpoints

### 1. Get Pending Transactions
```http
GET /wallet/transactions/pending
```
Returns all transactions with `status=pending`

### 2. Get Completed Transactions
```http
GET /wallet/transactions/completed
```
Returns all transactions with `status=success`

### 3. Get Filtered Transactions
```http
GET /wallet/transactions?status=pending&type=deposit
```
**Query Parameters:**
- `status`: `pending`, `success`, or `failed`
- `type`: `deposit`, `withdrawal`, or `transfer`
- `limit`: Number of results (default: 50)
- `offset`: Pagination offset (default: 0)

### 4. Get Transaction Summary
```http
GET /wallet/transactions/summary
```
Returns statistics:
- Total transactions by status
- Total amounts by type
- Pending amount
- Current balance

## Quick Example Workflow

```bash
# 1. View pending transactions
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/wallet/transactions/pending

# Output shows:
# [
#   {
#     "reference": "TXN-20251210081957-KBODC6JN",
#     "amount": 2000.0,
#     "status": "pending",
#     ...
#   }
# ]

# 2. Get payment URL for the transaction
# (You already have this from when you created the deposit)
# If you lost it, re-initialize a new deposit

# 3. Open payment URL in browser and complete payment

# 4. Wait 5-10 seconds for webhook

# 5. Check balance
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/wallet/balance

# Now shows updated balance!

# 6. View completed transactions
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/wallet/transactions/completed
```

## Troubleshooting

### Payment Completed but Balance Not Updated?
1. Check webhook logs in your terminal running the server
2. Verify webhook endpoint is accessible
3. Check transaction status:
   ```bash
   curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/wallet/deposit/YOUR_REFERENCE/status
   ```
4. If Paystack shows "success" but local shows "pending", manually trigger webhook or contact support

### Can't Find Payment URL?
If you lost the authorization URL:
1. Create a new deposit (old pending transaction will remain)
2. Or check your email - Paystack may have sent it
3. Or view transaction in Paystack dashboard

### Old Pending Transactions?
Pending transactions older than 24 hours typically expire on Paystack's side. You can:
1. Ignore them (they won't affect your balance)
2. Create a new deposit for the same amount
3. Optionally clean up old pending transactions via admin tools (future feature)

## API Documentation

All endpoints are documented in the interactive API docs:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Look for the "Wallet" section to see all new filtering and summary endpoints!

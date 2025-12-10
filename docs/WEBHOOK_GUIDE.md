# 🔔 Paystack Webhook Integration Guide

## Overview

The SecurePay Wallet uses Paystack webhooks to receive real-time payment notifications. When a customer completes a payment, Paystack sends a webhook event to your server, which automatically credits the user's wallet.

## How It Works

### Payment Flow

```
┌─────────┐         ┌──────────┐         ┌──────────┐         ┌─────────┐
│  User   │────────▶│  Wallet  │────────▶│ Paystack │────────▶│  User   │
│         │ Deposit │   API    │ Payment │ Checkout │  Pays   │         │
└─────────┘         └──────────┘         └──────────┘         └─────────┘
                          │                     │
                          │    Webhook Event    │
                          │◀────────────────────┘
                          │
                          ▼
                    ┌──────────┐
                    │  Credit  │
                    │  Wallet  │
                    └──────────┘
```

### Step-by-Step Process

1. **User Initiates Deposit**
   - User calls `POST /wallet/deposit` with amount
   - API creates a pending transaction in database
   - API calls Paystack to initialize payment
   - Returns authorization URL to user

2. **User Completes Payment**
   - User opens authorization URL in browser
   - Enters card details and completes payment
   - Paystack processes the payment

3. **Paystack Sends Webhook**
   - On successful payment, Paystack sends `charge.success` event
   - Webhook includes signature for verification
   - Contains transaction reference and amount

4. **API Processes Webhook**
   - Verifies webhook signature (security)
   - Finds transaction by reference
   - Checks idempotency (prevents double-crediting)
   - Credits user's wallet
   - Updates transaction status to "success"

## Webhook Endpoint

### URL
```
POST /webhook/paystack
```

### Security

The webhook endpoint uses **HMAC SHA512** signature verification to ensure requests are genuinely from Paystack:

```python
# Paystack sends signature in header
X-Paystack-Signature: <signature>

# We verify it matches our calculation
expected = hmac.new(webhook_secret, payload, sha512).hexdigest()
if signature != expected:
    reject_request()
```

**Important**: Never process webhooks without signature verification!

## Webhook Event Structure

### charge.success Event

```json
{
  "event": "charge.success",
  "data": {
    "reference": "TXN-20251210123456-ABCD1234",
    "amount": 100000,
    "status": "success",
    "paid_at": "2025-12-10T12:34:56.000Z",
    "customer": {
      "email": "user@example.com",
      "customer_code": "CUS_xxxxxxxxxx"
    },
    "metadata": {},
    "channel": "card",
    "currency": "NGN"
  }
}
```

### Key Fields

- **reference**: Unique transaction ID (matches our database)
- **amount**: Amount in kobo (divide by 100 for NGN)
- **status**: Payment status ("success", "failed", etc.)
- **paid_at**: Timestamp of payment completion

## Idempotency Protection

The webhook handler implements **idempotency** to prevent duplicate processing:

```python
# Check if already processed
if transaction.status == "success":
    return {"status": "already_processed"}

# Only credit wallet if not already done
```

### Why Idempotency Matters

1. **Network Issues**: Paystack may retry failed webhook deliveries
2. **Timeouts**: Your server might process but fail to respond
3. **Testing**: During development, webhooks may be replayed

**Result**: Without idempotency, a user could be credited multiple times for one payment!

## Testing Webhooks Locally

### Option 1: ngrok (Recommended)

```bash
# Install ngrok
npm install -g ngrok
# or
brew install ngrok

# Start your local server
uvicorn main:app --reload

# In another terminal, expose it
ngrok http 8000

# Output shows your public URL:
# Forwarding: https://abc123.ngrok.io -> http://localhost:8000
```

**Configure Paystack:**
1. Go to Paystack Dashboard → Settings → Webhooks
2. Set webhook URL: `https://abc123.ngrok.io/webhook/paystack`
3. Copy webhook secret to `.env` file

### Option 2: Paystack CLI (For Testing)

```bash
# Install Paystack CLI
npm install -g @paystack/cli

# Send test webhook
paystack webhooks test charge.success \
  --url http://localhost:8000/webhook/paystack \
  --reference TXN-TEST-001
```

### Option 3: Manual cURL Test

```bash
# Calculate signature
SECRET="your_webhook_secret"
PAYLOAD='{"event":"charge.success","data":{"reference":"TXN-TEST-001","amount":100000,"status":"success"}}'
SIGNATURE=$(echo -n "$PAYLOAD" | openssl sha512 -hmac "$SECRET" | cut -d' ' -f2)

# Send request
curl -X POST http://localhost:8000/webhook/paystack \
  -H "X-Paystack-Signature: $SIGNATURE" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD"
```

## Monitoring Webhooks

### Check Webhook Logs

**In Paystack Dashboard:**
- Settings → Webhooks → View Logs
- Shows all webhook attempts
- HTTP status codes (200 = success)
- Response times
- Retry attempts

### Common Response Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Webhook processed correctly |
| 401 | Unauthorized | Invalid signature - check webhook secret |
| 404 | Not Found | Transaction reference not in database |
| 400 | Bad Request | Amount mismatch or missing fields |
| 500 | Server Error | Check server logs for errors |

## Webhook Best Practices

### 1. Always Verify Signatures
```python
if not verify_signature(payload, signature):
    raise HTTPException(401, "Invalid signature")
```

### 2. Implement Idempotency
```python
if transaction.status == "success":
    return {"status": "already_processed"}
```

### 3. Validate Amounts
```python
if transaction.amount != webhook_amount:
    mark_as_failed("Amount mismatch")
```

### 4. Respond Quickly
- Acknowledge webhook within 5 seconds
- Process heavy operations asynchronously
- Paystack times out after 15 seconds

```python
# Good: Quick response
await quick_validation()
return {"status": "received"}

# Bad: Slow processing
await send_email()  # Do this async!
await update_analytics()  # Do this async!
return {"status": "success"}
```

### 5. Log Everything
```python
logger.info(f"Webhook received: {reference}")
logger.info(f"Transaction credited: {amount} to wallet {wallet_id}")
```

## Troubleshooting

### Webhook Not Received

**Checklist:**
- [ ] Server is publicly accessible (not localhost)
- [ ] Webhook URL configured in Paystack Dashboard
- [ ] Webhook secret matches `.env` file
- [ ] Firewall allows Paystack IPs
- [ ] SSL certificate valid (for HTTPS)

### Signature Verification Fails

```python
# Common issues:
1. Wrong webhook secret in .env
2. Body modified before verification
3. Signature header not read correctly
4. Using wrong hashing algorithm (must be SHA512)
```

**Debug:**
```python
print(f"Expected: {expected_signature}")
print(f"Received: {received_signature}")
print(f"Body: {body.decode()}")
```

### Duplicate Credits

- **Cause**: Idempotency not implemented
- **Fix**: Check transaction status before crediting
- **Result**: Our implementation already handles this!

### Amount Mismatch

```python
# Webhook shows: 100000 kobo
# Database shows: 1000 NGN
# Match!

# Wrong:
if webhook_amount != db_amount:  # 100000 != 1000 ❌

# Correct:
if (webhook_amount / 100) != db_amount:  # 1000 == 1000 ✅
```

## Production Deployment

### Required Environment Variables

```bash
# .env
PAYSTACK_SECRET_KEY=sk_live_xxxxxxxxxxxxx
PAYSTACK_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx
FRONTEND_URL=https://yourdomain.com
```

### Webhook URL Setup

1. **Get your domain**: `https://api.yourdomain.com`
2. **Set webhook URL**: `https://api.yourdomain.com/webhook/paystack`
3. **Use HTTPS**: Required for production
4. **Test first**: Use Paystack test mode before going live

### Webhook Secret Rotation

If webhook secret is compromised:

1. Generate new secret in Paystack Dashboard
2. Update `.env` file
3. Restart application
4. Test with new secret
5. Old webhooks will fail (expected)

## Code Reference

### Main Webhook Handler
**File**: `routers/webhook_routes.py`

**Key Functions**:
- `paystack_webhook()` - Main webhook handler
- Signature verification
- Idempotency check
- Wallet crediting

### Paystack Service
**File**: `services/paystack.py`

**Key Functions**:
- `verify_webhook_signature()` - HMAC verification
- `initialize_transaction()` - Start payment
- `verify_transaction()` - Manual status check

## Testing Checklist

- [ ] Test successful payment
- [ ] Test failed payment
- [ ] Test duplicate webhook (idempotency)
- [ ] Test amount mismatch
- [ ] Test invalid signature
- [ ] Test missing reference
- [ ] Test missing wallet
- [ ] Check transaction status updates
- [ ] Verify wallet balance changes
- [ ] Test webhook retry logic

## Support

**Paystack Documentation**:
- [Webhooks Overview](https://paystack.com/docs/payments/webhooks/)
- [Testing Guide](https://paystack.com/docs/payments/test-payments/)
- [Webhook Events](https://paystack.com/docs/payments/webhooks/#supported-events)

**SecurePay Wallet Support**:
- Check API docs: http://localhost:8000/docs
- View logs: Check application logs
- Test endpoint: `GET /wallet/deposit/{reference}/status`

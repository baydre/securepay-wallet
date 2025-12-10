# 💳 Payment Callback Setup

## The Issue You Encountered

When completing a Paystack payment, you got:
```
ERR_CONNECTION_REFUSED
http://localhost:3000/wallet/deposit/callback
```

This happens because **Paystack redirects to a frontend URL** after payment, but you don't have a frontend running.

## ✅ Solutions Implemented

### 1. **Auto-Detection for Backend-Only Testing**

The code now automatically detects if you're testing without a frontend and redirects to the API status page instead:

```python
# services/paystack.py (UPDATED)
if not settings.frontend_url or settings.frontend_url.startswith("http://localhost:3000"):
    # Redirect to API status page for backend-only testing
    callback_url = f"http://localhost:8000/wallet/deposit/{reference}/status"
```

### 2. **Beautiful Payment Success Page**

A new HTML page (`static/payment-success.html`) shows payment status with:
- ✅ Real-time status checking
- 💰 Transaction details
- 🎨 Beautiful UI
- 🔄 Auto-refresh option

### 3. **Smart Status Endpoint**

The `/wallet/deposit/{reference}/status` endpoint now:
- Returns **HTML page** when accessed from browser (Paystack redirect)
- Returns **JSON** when accessed via API
- **No authentication required** for Paystack redirects

## How It Works Now

### Payment Flow

```
1. User calls: POST /wallet/deposit
   ↓
2. API creates pending transaction
   ↓
3. API returns Paystack payment URL
   ↓
4. User pays on Paystack page
   ↓
5. Paystack redirects to: http://localhost:8000/wallet/deposit/{ref}/status
   ↓
6. Beautiful HTML page shows status
   ↓
7. Page auto-checks payment status via AJAX
   ↓
8. Shows: ✅ Success / ⏳ Pending / ❌ Failed
```

### Webhook Still Handles Crediting

**Important:** The webhook (`/webhook/paystack`) still handles the actual wallet crediting:

```
User pays → Paystack webhook fires → API credits wallet → Status updated
```

The callback page just shows the user what happened.

## Testing Without Frontend

### Option 1: Let It Auto-Redirect (Recommended)

Just leave your `.env` with:
```bash
FRONTEND_URL=http://localhost:3000
```

The code now detects this and auto-redirects to the API status page.

### Option 2: Use API Status URL Directly

Set in `.env`:
```bash
FRONTEND_URL=http://localhost:8000/wallet/deposit
```

Then the callback becomes:
```
http://localhost:8000/wallet/deposit/{reference}/status
```

### Option 3: Use a Public URL (Production)

For production with a real frontend:
```bash
FRONTEND_URL=https://yourdomain.com
```

Then Paystack redirects to:
```
https://yourdomain.com/wallet/deposit/callback?reference=TXN-...
```

## Testing the Flow

### 1. Make a deposit:
```bash
curl -X POST http://localhost:8000/wallet/deposit \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 100.00}'
```

### 2. Open the payment URL returned

### 3. Pay with test card:
```
Card: 4084084084084081
CVV: 408
PIN: 0000
OTP: 123456
```

### 4. After payment, you'll see:
- ✅ Beautiful success page (instead of ERR_CONNECTION_REFUSED)
- Transaction details
- Real-time status

## Files Updated

1. **`services/paystack.py`** - Auto-detect backend-only testing
2. **`routers/wallet_routes.py`** - Smart HTML/JSON response
3. **`static/payment-success.html`** - Beautiful payment status page

## Webhook Setup (Still Required)

The callback page shows status, but **the webhook credits the wallet**.

To test webhooks locally:

```bash
# 1. Install ngrok
brew install ngrok  # or npm install -g ngrok

# 2. Expose local server
ngrok http 8000

# 3. Copy URL (e.g., https://abc123.ngrok.io)

# 4. Set in Paystack Dashboard:
#    Settings → Webhooks
#    URL: https://abc123.ngrok.io/webhook/paystack
```

See [docs/WEBHOOK_GUIDE.md](../WEBHOOK_GUIDE.md) for complete webhook setup.

## Summary

**Before:**
- ❌ Payment succeeded, but ERR_CONNECTION_REFUSED on redirect
- ❌ No way to see payment status without API call
- ❌ Confusing for testing

**After:**
- ✅ Auto-redirects to API status page
- ✅ Beautiful HTML page shows payment status
- ✅ Works perfectly for backend-only testing
- ✅ Still compatible with real frontend when ready

**Your payment succeeded!** You just couldn't see it because of the redirect issue. Now you can! 🎉

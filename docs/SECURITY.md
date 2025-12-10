# OAuth & JWT Security Best Practices

## ⚠️ JWT Token in URL - Security Concerns

### **The Problem:**
Currently, the OAuth callback redirects with the JWT token in the URL:
```
http://localhost:3000/auth/callback?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### **Why This Is Bad:**
1. **Browser History** - Token is stored in browser history
2. **Server Logs** - Appears in web server access logs
3. **Referrer Headers** - May be leaked to third-party sites
4. **Shoulder Surfing** - Visible in address bar
5. **Bookmarks** - Could be accidentally saved
6. **Shared URLs** - Easy to accidentally share

### **Better Approaches:**

#### **Option 1: HTTP-Only Cookies (Recommended for Web)**
```python
response = RedirectResponse(url=frontend_url)
response.set_cookie(
    key="access_token",
    value=access_token,
    httponly=True,  # JavaScript can't access
    secure=True,    # HTTPS only
    samesite="lax", # CSRF protection
    max_age=1800    # 30 minutes
)
```
✅ **Pros**: Most secure, automatic transmission, XSS protection
❌ **Cons**: Requires CORS configuration, not great for mobile apps

#### **Option 2: POST Message to Frontend**
```html
<!-- Backend returns HTML that posts to frontend -->
<form id="tokenForm" action="http://frontend.com/auth" method="POST">
    <input type="hidden" name="token" value="JWT_TOKEN">
</form>
<script>document.getElementById('tokenForm').submit();</script>
```
✅ **Pros**: Token not in URL, works cross-domain
❌ **Cons**: More complex, requires frontend handling

#### **Option 3: State Parameter + Backend Session**
```python
# Store token in backend session
# Pass only a state ID to frontend
# Frontend exchanges state for token via API call
```
✅ **Pros**: Most secure, tokens never exposed
❌ **Cons**: Requires session storage, more API calls

## 🔒 Current Implementation

For **development/testing**, the app now:
1. Returns JSON response with token when no frontend is detected
2. You can use the test page at: `http://localhost:8000/static/auth-test.html`
3. Token is displayed securely within the app

For **production** with frontend:
1. Uses HTTP-only cookies
2. Falls back to URL parameter only if needed
3. Always use HTTPS in production

## 🧪 Testing Without Frontend

### Method 1: Use the Test Page
```bash
# Open in browser
http://localhost:8000/static/auth-test.html
```

### Method 2: Direct API Call
```bash
# 1. Get token from OAuth
curl -X GET "http://localhost:8000/auth/google" -L

# 2. After auth, check response JSON for token

# 3. Use token in API
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/auth/me
```

### Method 3: Swagger UI
```bash
# Open Swagger
http://localhost:8000/docs

# 1. Click "Authorize" button
# 2. Complete OAuth flow
# 3. Paste token in Bearer auth
# 4. Test all endpoints
```

## 🎯 Recommendations

### For Development:
- ✅ Current implementation (JSON response) is fine
- ✅ Use the test HTML page
- ✅ Token exposure is acceptable for testing

### For Production:
1. **Use HTTPS everywhere** (mandatory)
2. **Implement HTTP-only cookies** for web apps
3. **Use authorization code flow** for mobile apps
4. **Add refresh tokens** for long sessions
5. **Implement token rotation**
6. **Add rate limiting** on auth endpoints
7. **Monitor for suspicious activity**

### Additional Security Measures:
```python
# 1. Short-lived access tokens
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Not 30

# 2. Implement refresh tokens
REFRESH_TOKEN_EXPIRE_DAYS = 7

# 3. Add token revocation
# Store active tokens in Redis/database
# Check on each request

# 4. Add device fingerprinting
# Track where tokens are used

# 5. Implement MFA
# Require second factor for sensitive operations
```

## 📚 Further Reading
- [OWASP JWT Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
- [OAuth 2.0 Security Best Practices](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics)
- [HTTP-Only Cookies Explained](https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies#security)

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request
from starlette.responses import RedirectResponse
import models
from schemas import Token
from auth import create_access_token
from dependencies import get_db, get_current_user
from config import get_settings

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Configure OAuth
oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)


@router.get("/google")
async def google_login(request: Request):
    """
    Redirect to Google OAuth login page
    """
    redirect_uri = settings.google_redirect_uri
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Handle Google OAuth callback and create/login user
    
    SECURITY NOTE: For production, use HTTP-only cookies instead of URL parameters
    to avoid JWT token exposure in browser history and logs.
    """
    try:
        # Get the OAuth token
        token = await oauth.google.authorize_access_token(request)
        
        # Get user info from Google
        user_info = token.get('userinfo')
        
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Google"
            )
        
        email = user_info.get('email')
        google_id = user_info.get('sub')
        full_name = user_info.get('name')
        
        if not email or not google_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email or Google ID not provided"
            )
        
        # Check if user exists
        user = db.query(models.User).filter(models.User.email == email).first()
        
        if not user:
            # Create new user
            user = models.User(
                email=email,
                google_id=google_id,
                full_name=full_name
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # Create wallet for new user
            wallet = models.Wallet(
                user_id=user.id,
                wallet_number=models.Wallet.generate_wallet_number(),
                balance=0.0
            )
            db.add(wallet)
            db.commit()
        
        # Create JWT access token
        access_token = create_access_token(data={"sub": user.email})
        
        # For development/testing: Return JSON with token
        # For production with frontend: Redirect with secure cookie
        # Check if request is from browser or API client
        accept_header = request.headers.get('accept', '')
        
        if 'application/json' in accept_header or not settings.frontend_url or settings.frontend_url == 'http://localhost:3000':
            # Return JSON response (for testing without frontend)
            return {
                "status": "success",
                "message": "Authentication successful",
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "email": user.email,
                    "full_name": user.full_name,
                    "wallet_number": user.wallet.wallet_number if user.wallet else None
                }
            }
        else:
            # Production: Redirect to frontend
            # BETTER PRACTICE: Set HTTP-only cookie instead
            response = RedirectResponse(url=f"{settings.frontend_url}/auth/callback")
            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,  # Prevents JavaScript access (XSS protection)
                secure=True,    # Only sent over HTTPS in production
                samesite="lax", # CSRF protection
                max_age=1800    # 30 minutes
            )
            return response
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"OAuth Error: {error_detail}")  # Log full error for debugging
        
        # Return JSON error for testing
        return {
            "status": "error",
            "message": "Authentication failed",
            "detail": str(e),
            "error_type": type(e).__name__
        }


@router.get("/me")
async def get_current_user_info(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user information
    Requires: Authorization header with Bearer token
    """
    # Get wallet info
    wallet = db.query(models.Wallet).filter(
        models.Wallet.user_id == current_user.id
    ).first()
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "created_at": current_user.created_at,
        "wallet": {
            "wallet_number": wallet.wallet_number if wallet else None,
            "balance": wallet.balance if wallet else 0.0
        } if wallet else None
    }

from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # Database
    database_url: str
    
    # JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Google OAuth
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str = ""  # Will be set dynamically
    
    # Paystack
    paystack_secret_key: str
    paystack_public_key: str
    paystack_webhook_secret: str
    
    # Application
    app_name: str = "SecurePay Wallet"
    app_version: str = "1.0.0"
    frontend_url: str = ""  # Will be set dynamically
    backend_url: str = ""  # Will be set dynamically
    
    # Environment detection
    environment: str = "development"  # 'development', 'production', or 'staging'
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def __init__(self, **data):
        super().__init__(**data)
        
        # Auto-detect environment based on database URL or ENVIRONMENT variable
        if not self.environment or self.environment == "development":
            # Check if production database is being used
            if "localhost" not in self.database_url:
                self.environment = "production"
            elif "ENVIRONMENT" in os.environ:
                self.environment = os.environ.get("ENVIRONMENT", "development").lower()
        
        # Set URLs based on environment if not explicitly provided
        # Check if URLs were explicitly set in .env (not just default values)
        env_backend_url = os.getenv("BACKEND_URL", "")
        env_frontend_url = os.getenv("FRONTEND_URL", "")
        env_redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "")
        
        # Only use auto-detected values if env vars aren't set
        if not env_backend_url:
            self.backend_url = (
                "https://api-securepay-wallet.mooo.com" 
                if self.environment == "production" 
                else "http://localhost:8000"
            )
        
        if not env_frontend_url:
            self.frontend_url = (
                "https://api-securepay-wallet.mooo.com" 
                if self.environment == "production" 
                else "http://localhost:3000"
            )
        
        if not env_redirect_uri:
            self.google_redirect_uri = (
                "https://api-securepay-wallet.mooo.com/auth/google/callback"
                if self.environment == "production"
                else "http://localhost:8000/auth/google/callback"
            )


@lru_cache()
def get_settings() -> Settings:
    return Settings()

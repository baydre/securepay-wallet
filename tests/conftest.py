"""
Pytest configuration and shared fixtures
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
import models
from database import Base
from main import app
from dependencies import get_db
import auth

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with overridden database dependency"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing"""
    user = models.User(
        email="test@example.com",
        google_id="test_google_id_123",
        name="Test User"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_wallet(db_session, sample_user):
    """Create a sample wallet for testing"""
    wallet = models.Wallet(
        user_id=sample_user.id,
        wallet_number=f"WAL{sample_user.id:010d}",
        balance=1000.00
    )
    db_session.add(wallet)
    db_session.commit()
    db_session.refresh(wallet)
    return wallet


@pytest.fixture
def auth_token(sample_user):
    """Generate a valid JWT token for testing"""
    from datetime import timedelta
    token = auth.create_access_token(
        data={"sub": sample_user.email, "user_id": sample_user.id},
        expires_delta=timedelta(minutes=30)
    )
    return token


@pytest.fixture
def auth_headers(auth_token):
    """Return authentication headers with JWT token"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def sample_api_key(db_session, sample_user):
    """Create a sample API key for testing"""
    from datetime import datetime, timedelta
    
    raw_key = "test_api_key_123456789"
    hashed_key = auth.hash_api_key(raw_key)
    
    api_key = models.APIKey(
        user_id=sample_user.id,
        name="Test API Key",
        key_hash=hashed_key,
        permissions=["read", "deposit"],
        expires_at=datetime.utcnow() + timedelta(days=30)
    )
    db_session.add(api_key)
    db_session.commit()
    db_session.refresh(api_key)
    
    # Return both the key object and the raw key
    api_key.raw_key = raw_key
    return api_key

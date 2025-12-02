"""
Authentication router.
Handles user registration, login, and API key management.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uuid
from datetime import datetime, timedelta
from typing import Optional
import logging

from auth_models import (
    UserCreate, UserLogin, Token, AuthService, TokenData,
    APIKeyCreate, APIKeyResponse
)
from connection_manager import connection_manager
from config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()
logger = logging.getLogger(__name__)

@router.post("/register", response_model=Token)
async def register(user: UserCreate):
    """
    Register a new user and create their tenant.
    
    Args:
        user: User registration data
        
    Returns:
        JWT access token
    """
    pool = await connection_manager.get_pool()
    
    async with pool.acquire() as conn:
        # Check if user exists
        existing = await conn.fetchrow(
            "SELECT id FROM optischema.users WHERE email = $1",
            user.email
        )
        
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create tenant
        tenant_id = str(uuid.uuid4())
        tenant_name = user.tenant_name or f"{user.name}'s Workspace"
        
        await conn.execute("""
            INSERT INTO optischema.tenants (id, name, created_at)
            VALUES ($1, $2, NOW())
        """, tenant_id, tenant_name)
        
        logger.info(f"Created tenant: {tenant_id} ({tenant_name})")
        
        # Create user
        user_id = str(uuid.uuid4())
        password_hash = AuthService.hash_password(user.password)
        
        await conn.execute("""
            INSERT INTO optischema.users (
                id, tenant_id, email, password_hash, name, created_at
            ) VALUES ($1, $2, $3, $4, $5, NOW())
        """, user_id, tenant_id, user.email, password_hash, user.name)
        
        logger.info(f"Created user: {user_id} ({user.email})")
        
        # Generate token
        access_token = AuthService.create_access_token(
            user_id,
            tenant_id,
            user.email,
            settings.jwt_secret,
            settings.jwt_expiration_hours
        )
        
        return Token(
            access_token=access_token,
            expires_in=settings.jwt_expiration_hours * 3600
        )

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """
    Login user with email and password.
    
    Args:
        credentials: User login credentials
        
    Returns:
        JWT access token
    """
    pool = await connection_manager.get_pool()
    
    async with pool.acquire() as conn:
        user = await conn.fetchrow("""
            SELECT id, tenant_id, email, password_hash, is_active
            FROM optischema.users
            WHERE email = $1
        """, credentials.email)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        if not user['is_active']:
            raise HTTPException(status_code=403, detail="Account is disabled")
        
        if not AuthService.verify_password(credentials.password, user['password_hash']):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Generate token
        access_token = AuthService.create_access_token(
            str(user['id']),
            str(user['tenant_id']),
            user['email'],
            settings.jwt_secret,
            settings.jwt_expiration_hours
        )
        
        logger.info(f"User logged in: {user['email']}")
        
        return Token(
            access_token=access_token,
            expires_in=settings.jwt_expiration_hours * 3600
        )

@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    api_key_data: APIKeyCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Create a new API key for programmatic access.
    
    Args:
        api_key_data: API key creation data
        credentials: User's JWT token
        
    Returns:
        API key information (key is only shown once)
    """
    # Verify user token
    token_data = AuthService.verify_token(credentials.credentials, settings.jwt_secret)
    
    pool = await connection_manager.get_pool()
    
    async with pool.acquire() as conn:
        # Generate API key
        api_key = AuthService.generate_api_key()
        key_hash = AuthService.hash_api_key(api_key)
        
        # Calculate expiration
        expires_at = None
        if api_key_data.expires_days:
            expires_at = datetime.utcnow() + timedelta(days=api_key_data.expires_days)
        
        # Store API key
        key_id = str(uuid.uuid4())
        await conn.execute("""
            INSERT INTO optischema.api_keys (
                id, user_id, tenant_id, key_hash, name, expires_at, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
        """, key_id, token_data.user_id, token_data.tenant_id, key_hash, api_key_data.name, expires_at)
        
        logger.info(f"Created API key: {key_id} for user {token_data.user_id}")
        
        return APIKeyResponse(
            id=key_id,
            key=api_key,  # Only shown once!
            name=api_key_data.name,
            created_at=datetime.utcnow(),
            expires_at=expires_at
        )

@router.get("/me")
async def get_current_user(request: Request):
    """
    Get current user information from request context.
    
    Args:
        request: FastAPI request with user context
        
    Returns:
        User information
    """
    return {
        "user_id": request.state.user_id,
        "tenant_id": request.state.tenant_id,
        "email": request.state.email
    }

async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """
    Dependency to get current authenticated user from token.
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        Token data with user information
    """
    return AuthService.verify_token(credentials.credentials, settings.jwt_secret)

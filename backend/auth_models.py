"""
Authentication models and utilities.
Handles user authentication, JWT tokens, and password hashing.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, timedelta
from fastapi import HTTPException
import jwt
import bcrypt
import logging

logger = logging.getLogger(__name__)

class UserCreate(BaseModel):
    """User registration model."""
    email: EmailStr
    password: str = Field(min_length=8, description="Password must be at least 8 characters")
    name: str = Field(min_length=1, description="User's full name")
    tenant_name: Optional[str] = Field(None, description="Optional tenant/workspace name")

class UserLogin(BaseModel):
    """User login model."""
    email: EmailStr
    password: str

class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400  # 24 hours in seconds

class TokenData(BaseModel):
    """Token payload data."""
    user_id: str
    tenant_id: str
    email: str
    exp: datetime

class APIKeyCreate(BaseModel):
    """API key creation model."""
    name: str = Field(description="Name/description for this API key")
    expires_days: Optional[int] = Field(None, description="Days until expiration (None = never)")

class APIKeyResponse(BaseModel):
    """API key response."""
    id: str
    key: str  # Only shown once during creation
    name: str
    created_at: datetime
    expires_at: Optional[datetime]

class AuthService:
    """Authentication service with password hashing and JWT management."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using bcrypt.
        
        Args:
            password: Plaintext password
            
        Returns:
            Hashed password string
        """
        try:
            salt = bcrypt.gensalt(rounds=12)
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            return hashed.decode('utf-8')
        except Exception as e:
            logger.error(f"Password hashing failed: {e}")
            raise HTTPException(status_code=500, detail="Password hashing failed")
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """
        Verify password against hash.
        
        Args:
            password: Plaintext password to verify
            hashed: Hashed password from database
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False
    
    @staticmethod
    def create_access_token(
        user_id: str,
        tenant_id: str,
        email: str,
        jwt_secret: str,
        expiration_hours: int = 24
    ) -> str:
        """
        Create JWT access token.
        
        Args:
            user_id: User's unique ID
            tenant_id: User's tenant ID
            email: User's email
            jwt_secret: Secret key for signing
            expiration_hours: Token expiration in hours
            
        Returns:
            JWT token string
        """
        try:
            expires = datetime.utcnow() + timedelta(hours=expiration_hours)
            
            payload = {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "email": email,
                "exp": expires,
                "iat": datetime.utcnow()
            }
            
            token = jwt.encode(payload, jwt_secret, algorithm="HS256")
            return token
        except Exception as e:
            logger.error(f"Token creation failed: {e}")
            raise HTTPException(status_code=500, detail="Token creation failed")
    
    @staticmethod
    def verify_token(token: str, jwt_secret: str) -> TokenData:
        """
        Verify and decode JWT token.
        
        Args:
            token: JWT token string
            jwt_secret: Secret key for verification
            
        Returns:
            TokenData with user information
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
            
            return TokenData(
                user_id=payload["user_id"],
                tenant_id=payload["tenant_id"],
                email=payload["email"],
                exp=datetime.fromtimestamp(payload["exp"])
            )
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise HTTPException(status_code=401, detail="Token verification failed")
    
    @staticmethod
    def generate_api_key() -> str:
        """
        Generate a secure random API key.
        
        Returns:
            Random API key string
        """
        import secrets
        return f"osk_{secrets.token_urlsafe(32)}"  # osk = OptiSchema Key
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """
        Hash API key for storage.
        
        Args:
            api_key: Plaintext API key
            
        Returns:
            Hashed API key
        """
        return AuthService.hash_password(api_key)
    
    @staticmethod
    def verify_api_key(api_key: str, hashed: str) -> bool:
        """
        Verify API key against hash.
        
        Args:
            api_key: Plaintext API key
            hashed: Hashed API key from database
            
        Returns:
            True if API key matches, False otherwise
        """
        return AuthService.verify_password(api_key, hashed)

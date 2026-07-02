"""
Security Module - Password Hashing, JWT Token Management, and OAuth2

Security Best Practices Implemented:
1. bcrypt for password hashing (intentionally slow, resistant to brute-force)
2. JWT with short expiration (30 minutes)
3. OAuth2 Password Bearer flow
4. Secure token validation with proper error handling
5. Environment-based secret key (in production)

Why bcrypt over MD5/SHA-256:
- MD5 and SHA-256 are designed to be fast, making them vulnerable to brute-force attacks
- bcrypt is intentionally slow (has a work factor) making brute-force computationally expensive
- bcrypt includes a salt automatically, preventing rainbow table attacks
"""

from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from jose import JWTError
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# Password hashing context with bcrypt
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

# JWT Configuration
SECRET_KEY = "mysecretkey123"  # In production, use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Why bcrypt:
    - Automatically generates and stores a salt
    - Configurable work factor (rounds) - 12 by default
    - Resistant to GPU-based brute-force attacks
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """
    Create a JWT access token
    
    JWT Token Structure:
    Header: {"alg": "HS256", "typ": "JWT"}
    Payload: {"sub": username, "exp": timestamp}
    Signature: HMAC-SHA256(header + "." + payload, secret)
    
    Note: JWT payloads are base64-encoded, not encrypted!
    Never store sensitive data (passwords, credit cards) in JWT payload.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> str:
    """
    Verify and decode a JWT token
    
    Returns the username if token is valid
    Raises HTTPException 401 if token is invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
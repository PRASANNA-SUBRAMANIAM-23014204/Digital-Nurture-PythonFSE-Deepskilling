from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import User
from schemas import UserCreate, UserLogin, Token, UserResponse
from security import hash_password, verify_password, create_access_token, verify_token

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def send_confirmation_email(email: str):
    """Background task to simulate sending confirmation email"""
    print(f"[Email] Sending confirmation email to {email}")


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with hashed password using bcrypt"
)
async def register(
    user: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user
    
    - **username**: Unique alphanumeric username (3-50 characters)
    - **email**: Valid email address
    - **password**: Minimum 8 characters with at least one digit, uppercase, and lowercase
    
    Note: Password is hashed using bcrypt before storing.
    Never store plain-text passwords!
    """
    # Check if username already exists
    result = await db.execute(select(User).where(User.username == user.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered"
        )
    
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Hash password using bcrypt
    # Never store plain-text password!
    hashed_password = hash_password(user.password)
    
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    # Add background task to send confirmation email
    background_tasks.add_task(send_confirmation_email, user.email)
    
    # Return user without password hash
    return db_user


@router.post(
    "/login",
    response_model=Token,
    summary="Login and get JWT token",
    description="Authenticate user and receive JWT access token (valid for 30 minutes)"
)
async def login(
    user: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Login and receive JWT access token
    
    Returns:
    - **access_token**: JWT token for authentication
    - **token_type**: Always "bearer"
    
    The token should be included in subsequent requests as:
    Authorization: Bearer <access_token>
    """
    result = await db.execute(select(User).where(User.username == user.username))
    db_user = result.scalar_one_or_none()
    
    # Use bcrypt to verify password
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Check if user is active
    if not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Create JWT token
    access_token = create_access_token(data={"sub": db_user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get(
    "/verify",
    response_model=dict,
    summary="Verify JWT token",
    description="Check if a JWT token is valid and return the username"
)
async def verify_token_endpoint(token: str):
    """
    Verify if a JWT token is valid
    
    Returns the username if valid
    """
    username = verify_token(token)
    return {"valid": True, "username": username}
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

from cryptography.fernet import Fernet


#--------------------Password-----------------------

# Security utilities for password hashing and JWT token management
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash a plain password using bcrypt
def get_password_hash(password):
    return pwd_context.hash(password)


# Verify a plain password against a hashed password
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


# Create a JWT access token with the given data and expiration time
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now() + timedelta(
        minutes=expires_delta or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    
    
#-------------------email id -------------------------------
cipher = Fernet(settings.FERNET_KEY.encode())


def encrypt_text(text: str) -> str:
    return cipher.encrypt(text.encode()).decode()


def decrypt_text(token: str) -> str:
    return cipher.decrypt(token.encode()).decode()
from typing import Optional
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.core.config import settings

security = HTTPBearer(auto_error=False)           # Create an instance of HTTPBearer for token authentication


# Dependency to get the current user from the token
def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if not credentials:
        # Return fallback mock admin user for local development and Studio UI
        return {"id": 1, "username": "admin", "role_code": "admin", "user_type_name": "ADMIN", "email": "admin@example.com"}
        
    token = credentials.credentials                   # Extract the token from the credentials
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        if "user_type_name" not in payload:
            payload["user_type_name"] = "ADMIN"
        return payload

    except JWTError:
        # Fallback during local development testing
        return {"id": 1, "username": "admin", "role_code": "admin", "user_type_name": "ADMIN", "email": "admin@example.com"}



# from fastapi import Depends, HTTPException, status
# from jose import JWTError, jwt
# from app.core.config import settings
# from fastapi.security import OAuth2PasswordBearer

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# def get_current_user(token: str = Depends(oauth2_scheme)):

#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )

#     try:
#         payload = jwt.decode(
#             token,
#             settings.SECRET_KEY,
#             algorithms=[settings.ALGORITHM]
#         )

#         user_id = payload.get("id")

#         if user_id is None:
#             raise credentials_exception

#         return user_id

#     except JWTError:
#         raise credentials_exception
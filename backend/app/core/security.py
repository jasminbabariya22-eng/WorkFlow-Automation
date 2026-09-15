from cryptography.fernet import Fernet
from app.core.config import settings

cipher = Fernet(settings.FERNET_KEY.encode())

def encrypt_text(text: str) -> str:
    """Encrypts sensitive credentials (like DB passwords) before saving to PostgreSQL."""
    return cipher.encrypt(text.encode()).decode()

def decrypt_text(token: str) -> str:
    """Decrypts database passwords in memory for connection pooling."""
    return cipher.decrypt(token.encode()).decode()

import os
import base64
import hashlib
from typing import Optional
from cryptography.fernet import Fernet

def _get_fernet_key() -> bytes:
    """Derives a valid Fernet 32-byte url-safe base64 key from environment variables."""
    raw_secret = os.getenv("TOKEN_ENCRYPTION_KEY") or os.getenv("SECRET_KEY") or "agentic-rag-studio-default-key-32b"
    # Hash raw secret to guaranteed 32 bytes and base64-urlsafe encode
    key_bytes = hashlib.sha256(raw_secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(key_bytes)

def get_fernet() -> Fernet:
    return Fernet(_get_fernet_key())

def encrypt_token(token: Optional[str]) -> Optional[str]:
    """Encrypts sensitive OAuth tokens before database storage using Fernet."""
    if not token:
        return None
    try:
        f = get_fernet()
        return f.encrypt(token.encode("utf-8")).decode("utf-8")
    except Exception as e:
        print(f"[Crypto] Token encryption error: {e}")
        return token

def decrypt_token(encrypted_token: Optional[str]) -> Optional[str]:
    """Decrypts Fernet-encrypted OAuth tokens. Gracefully handles unencrypted legacy tokens."""
    if not encrypted_token:
        return None
    try:
        f = get_fernet()
        return f.decrypt(encrypted_token.encode("utf-8")).decode("utf-8")
    except Exception:
        # If decryption fails (e.g. legacy plain text token), return as-is
        return encrypted_token


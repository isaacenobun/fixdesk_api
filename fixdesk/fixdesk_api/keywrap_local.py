import os, base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from .crypto import new_nonce

from dotenv import load_dotenv
load_dotenv()

def _master_key() -> bytes:
    b64 = os.getenv("APP_MASTER_KEY")
    if not b64:
        raise RuntimeError(f"Missing env var APP_MASTER_KEY")
    mk = base64.b64decode(b64)
    if len(mk) != 32:
        raise RuntimeError("Master key must be 32 bytes (after base64 decode).")
    return mk

def wrap_dek(dek: bytes) -> tuple[bytes, bytes]:
    mk = _master_key()
    nonce = new_nonce()
    wrapped = AESGCM(mk).encrypt(nonce, dek, b"dek-wrap:v1")
    return wrapped, nonce

def unwrap_dek(wrapped: bytes, nonce: bytes) -> bytes:
    mk = _master_key()
    return AESGCM(mk).decrypt(nonce, wrapped, b"dek-wrap:v1")

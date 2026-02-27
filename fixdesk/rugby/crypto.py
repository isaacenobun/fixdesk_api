import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

DEK_BYTES = 32
NONCE_BYTES = 12

def new_dek() -> bytes:
    return os.urandom(DEK_BYTES)

def new_nonce() -> bytes:
    return os.urandom(NONCE_BYTES)

def encrypt_aead(dek: bytes, plaintext: bytes, *, aad: bytes) -> tuple[bytes, bytes]:
    nonce = new_nonce()
    ct = AESGCM(dek).encrypt(nonce, plaintext, aad)
    return ct, nonce

def decrypt_aead(dek: bytes, ciphertext: bytes, *, nonce: bytes, aad: bytes) -> bytes:
    return AESGCM(dek).decrypt(nonce, ciphertext, aad)

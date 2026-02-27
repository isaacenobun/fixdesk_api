from .models import SecretRecord
from .crypto import encrypt_aead, decrypt_aead
from .keys import get_current_version, get_dek

def _aad(record_id: int) -> bytes:
    return f"record={record_id}".encode()

def create_secret(plaintext: str) -> SecretRecord:
    v = get_current_version()
    dek = get_dek(v)

    # create placeholder to get record_id for AAD binding
    rec = SecretRecord.objects.create(ciphertext=b"", nonce=b"", key_version=v)

    ct, nonce = encrypt_aead(dek, plaintext.encode("utf-8"), aad=_aad(rec.id))
    rec.ciphertext = ct
    rec.nonce = nonce
    rec.save(update_fields=["ciphertext", "nonce"])
    return rec

def read_secret(rec: SecretRecord) -> str:
    dek = get_dek(rec.key_version)
    pt = decrypt_aead(dek, bytes(rec.ciphertext), nonce=bytes(rec.nonce), aad=_aad(rec.id))
    return pt.decode("utf-8")

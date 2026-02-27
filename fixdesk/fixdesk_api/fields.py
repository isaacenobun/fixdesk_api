import struct
from django.db import models
from .crypto import encrypt_aead, decrypt_aead
from .keys import get_current_version, get_dek


class EncryptedTextField(models.BinaryField):
    description = "AES-GCM encrypted text"

    def get_prep_value(self, value):
        if value is None:
            return value

        # Already encrypted (loading case)
        if isinstance(value, (bytes, bytearray)):
            return value

        version = get_current_version()
        dek = get_dek(version)

        # AAD binds to model + field
        aad = f"{self.model.__name__}:{self.name}".encode()

        ciphertext, nonce = encrypt_aead(
            dek,
            value.encode("utf-8"),
            aad=aad,
        )

        # Pack: version (2 bytes) + nonce (12 bytes) + ciphertext
        return struct.pack(">H", version) + nonce + ciphertext

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value

        version = struct.unpack(">H", value[:2])[0]
        nonce = value[2:14]
        ciphertext = value[14:]

        dek = get_dek(version)

        aad = f"{self.model.__name__}:{self.name}".encode()

        plaintext = decrypt_aead(
            dek,
            ciphertext,
            nonce=nonce,
            aad=aad,
        )

        return plaintext.decode("utf-8")

    def to_python(self, value):
        if isinstance(value, str) or value is None:
            return value
        return self.from_db_value(value, None, None)

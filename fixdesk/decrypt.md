🔐 Step-by-Step Manual Decryption
1️⃣ Grab the encrypted value from Postgres

Example:

SELECT first_name FROM fixdesk_api_user WHERE id = '...';


You’ll get something like:

\x0001b3d4... (hex output)


Copy that full bytea value.

2️⃣ Open Django shell
python manage.py shell

3️⃣ Decrypt manually
import struct
from fixdesk_api.models import Keyring
from fixdesk_api.keywrap_local import unwrap_dek
from fixdesk_api.crypto import decrypt_aead
from django.apps import apps

# Replace with your actual raw DB value
raw = <paste_the_bytes_here>

# Normalize
if isinstance(raw, memoryview):
    raw = raw.tobytes()

# Extract version
version = struct.unpack(">H", raw[:2])[0]
nonce = raw[2:14]
ciphertext = raw[14:]

# Get wrapped DEK
kr = Keyring.objects.get(version=version)

# Unwrap DEK using master key
dek = unwrap_dek(bytes(kr.dek_wrapped), bytes(kr.dek_nonce))

# Build AAD (must match field logic exactly)
aad = b"User:first_name"

plaintext = decrypt_aead(dek, ciphertext, nonce=nonce, aad=aad)

print(plaintext.decode())


You’ll see:

John
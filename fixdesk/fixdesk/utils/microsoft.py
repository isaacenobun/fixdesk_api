import time
import requests
import jwt
from jwt.algorithms import RSAAlgorithm
from django.conf import settings

JWKS_URL = "https://login.microsoftonline.com/common/discovery/v2.0/keys"

_cache = {"keys": None, "ts": 0}

def get_jwks():
    if _cache["keys"] and time.time() - _cache["ts"] < 86400:
        return _cache["keys"]
    data = requests.get(JWKS_URL, timeout=10).json()
    _cache["keys"] = data["keys"]
    _cache["ts"] = time.time()
    return data["keys"]

def verify_microsoft_token(id_token: str):
    header = jwt.get_unverified_header(id_token)
    kid = header.get("kid")

    jwks = get_jwks()
    key = next((k for k in jwks if k["kid"] == kid), None)
    if not key:
        raise Exception("Invalid signing key")

    public_key = RSAAlgorithm.from_jwk(key)

    payload = jwt.decode(
        id_token,
        public_key,
        algorithms=["RS256"],
        audience=settings.MS_CLIENT_ID,
        options={"require": ["exp", "iat"]},
    )

    return payload
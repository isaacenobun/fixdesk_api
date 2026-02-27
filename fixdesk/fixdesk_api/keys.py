from django.core.cache import cache
from django.db import transaction
from django.apps import apps
from .crypto import new_dek
from .keywrap_local import wrap_dek, unwrap_dek

CACHE_TTL = 300  # seconds


def get_keyring_model():
    return apps.get_model("fixdesk_api", "Keyring")


def _cache_key(version: int) -> str:
    return f"dek:v{version}"


@transaction.atomic
def ensure_keyring_initialized():
    Keyring = get_keyring_model()

    kr = Keyring.objects.order_by("-version").first()
    if kr:
        return kr

    dek = new_dek()
    wrapped, nonce = wrap_dek(dek)

    return Keyring.objects.create(
        version=1,
        dek_wrapped=wrapped,
        dek_nonce=nonce
    )


def get_current_version() -> int:
    return ensure_keyring_initialized().version


def get_dek(version: int) -> bytes:
    Keyring = get_keyring_model()

    ck = _cache_key(version)
    dek = cache.get(ck)
    if dek:
        return dek

    kr = Keyring.objects.get(version=version)
    dek = unwrap_dek(bytes(kr.dek_wrapped), bytes(kr.dek_nonce))

    cache.set(ck, dek, CACHE_TTL)
    return dek


@transaction.atomic
def rotate_key() -> int:
    Keyring = get_keyring_model()

    current = ensure_keyring_initialized()
    new_version = current.version + 1

    dek = new_dek()
    wrapped, nonce = wrap_dek(dek)

    Keyring.objects.create(
        version=new_version,
        dek_wrapped=wrapped,
        dek_nonce=nonce
    )

    return new_version

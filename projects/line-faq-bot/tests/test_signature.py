import base64
import hashlib
import hmac

from app.line_client import verify_signature

SECRET = "test-channel-secret"
BODY = b'{"events":[{"type":"message"}]}'


def _sign(body: bytes, secret: str) -> str:
    return base64.b64encode(
        hmac.new(secret.encode(), body, hashlib.sha256).digest()
    ).decode()


def test_valid_signature_passes():
    assert verify_signature(BODY, _sign(BODY, SECRET), SECRET)


def test_wrong_secret_fails():
    assert not verify_signature(BODY, _sign(BODY, "other-secret"), SECRET)


def test_tampered_body_fails():
    signature = _sign(BODY, SECRET)
    assert not verify_signature(b'{"events":[]}', signature, SECRET)


def test_empty_signature_fails():
    assert not verify_signature(BODY, "", SECRET)


def test_garbage_signature_fails():
    assert not verify_signature(BODY, "not-base64!!", SECRET)

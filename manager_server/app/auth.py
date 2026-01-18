import base64
import hmac
import hashlib
import json
import time
from typing import Dict, Any, Optional, Tuple


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    padding = '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode((s + padding).encode("ascii"))


def encode_jwt(payload: Dict[str, Any], secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_and_verify_jwt(token: str, secret: str, verify_exp: bool = True) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Returns (payload, error). If verification fails, payload is None and error has message.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None, "invalid token format"
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        sig = _b64url_decode(sig_b64)
        expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return None, "signature mismatch"
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        if verify_exp and isinstance(payload, dict) and "exp" in payload:
            now = int(time.time())
            if int(payload["exp"]) < now:
                return None, "token expired"
        return payload, None
    except Exception as e:
        return None, str(e)

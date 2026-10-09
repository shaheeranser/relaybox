"""HMAC-SHA256 request signing for outbound webhooks."""
from __future__ import annotations

import hashlib
import hmac
import time


def sign_request(secret: str, body: bytes, timestamp: int) -> str:
    hex_digest = hmac.new(
        secret.encode(),
        f"{timestamp}.{body.decode()}".encode(),
        hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={hex_digest}"


def build_headers(secret: str, body: bytes, event_type: str, delivery_id: str, attempt: int) -> dict[str, str]:
    timestamp = int(time.time())
    signature = sign_request(secret, body, timestamp)
    return {
        "X-Relaybox-Signature": signature,
        "X-Relaybox-Event-Type": event_type,
        "X-Relaybox-Delivery-Id": delivery_id,
        "X-Relaybox-Attempt": str(attempt),
        "Content-Type": "application/json",
    }

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import User, UserSession

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${key.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_hex, expected_hex = encoded.split("$")
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(
            password.encode(),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=32,
        )
        return hmac.compare_digest(actual, bytes.fromhex(expected_hex))
    except (TypeError, ValueError):
        return False


def token_hash(token: str) -> str:
    secret = get_settings().session_secret.encode()
    return hmac.new(secret, token.encode(), hashlib.sha256).hexdigest()


def create_session(db: Session, user: User) -> str:
    raw = secrets.token_urlsafe(32)
    db.add(
        UserSession(
            token_hash=token_hash(raw),
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=get_settings().session_hours),
        )
    )
    db.commit()
    return raw


def delete_session(db: Session, raw_token: str | None) -> None:
    if not raw_token:
        return
    db.execute(delete(UserSession).where(UserSession.token_hash == token_hash(raw_token)))
    db.commit()

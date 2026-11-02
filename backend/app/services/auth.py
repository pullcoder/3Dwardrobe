import hashlib
import hmac
import secrets
import time
from collections import defaultdict
from threading import Lock

from fastapi import Request
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import LoginSession, User

_attempts: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def limit_auth(key: str):
    """로컬 개발용 메모리 제한. 다중 프로세스 서비스에는 공유 제한기가 필요하다."""
    with _lock:
        now = time.time()
        _attempts[key] = [t for t in _attempts[key] if t > now - 60]
        if len(_attempts[key]) >= 20:
            raise AppError("RATE_LIMIT", "잠시 후 다시 시도해 주세요.", 429)
        _attempts[key].append(now)


def password_hash(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    value = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
    return f"{salt}:{value.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    return hmac.compare_digest(password_hash(password, hashed.split(":")[0]), hashed)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_session(db: Session, user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    db.execute(delete(LoginSession).where(LoginSession.expires_at < time.time()))
    db.add(
        LoginSession(token_hash=token_hash(token), user_id=user_id, expires_at=time.time() + 43200)
    )
    return token


def current_user(request: Request, db: Session) -> User:
    token = request.headers.get("authorization", "").removeprefix("Bearer ")
    session = db.get(LoginSession, token_hash(token))
    if not session or session.expires_at <= time.time():
        raise AppError("AUTH_REQUIRED", "로그인 후 다시 시도해 주세요.", 401)
    user = db.get(User, session.user_id)
    if not user:
        raise AppError("AUTH_REQUIRED", "로그인이 필요합니다.", 401)
    return user

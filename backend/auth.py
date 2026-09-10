from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256, scrypt
import base64
import secrets

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .config import settings
from .db import get_db
from .models import AuthSession, Membership, User


@dataclass
class AuthContext:
    user: User
    membership: Membership


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters")
    salt = secrets.token_bytes(16)
    digest = scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return "scrypt$16384$8$1${}${}".format(
        base64.urlsafe_b64encode(salt).decode(),
        base64.urlsafe_b64encode(digest).decode(),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, n, r, p, salt_value, digest_value = encoded.split("$", 5)
        if scheme != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_value.encode())
        expected = base64.urlsafe_b64decode(digest_value.encode())
        actual = scrypt(password.encode(), salt=salt, n=int(n), r=int(r), p=int(p))
        return secrets.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def token_hash(token: str) -> str:
    return sha256(token.encode()).hexdigest()


def create_session(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(48)
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=token_hash(token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.session_ttl_days),
        )
    )
    return token


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def get_context(request: Request, db: Session) -> AuthContext:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="نیاز به ورود دارید")
    session = db.scalar(
        select(AuthSession)
        .options(selectinload(AuthSession.user).selectinload(User.memberships).selectinload(Membership.workspace))
        .where(AuthSession.token_hash == token_hash(token), AuthSession.revoked_at.is_(None))
    )
    now = datetime.now(timezone.utc)
    if not session or as_utc(session.expires_at) <= now or not session.user.is_active:
        raise HTTPException(status_code=401, detail="نشست شما منقضی شده است")
    if not session.user.memberships:
        raise HTTPException(status_code=403, detail="دسترسی به فضای کاری ندارید")
    return AuthContext(user=session.user, membership=session.user.memberships[0])


def require_auth(request: Request, db: Session = Depends(get_db)) -> AuthContext:
    return get_context(request, db)

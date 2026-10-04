"""User accounts, password hashing and JWT issuing/verification.

Passwords: Argon2id (argon2-cffi) when installed, otherwise stdlib scrypt. The scheme is stored
as a prefix in the hash, so both verify correctly. JWT: HS256 via PyJWT with an expiry claim.
"""
import base64
import hashlib
import hmac
import os
import re
from datetime import timedelta
from typing import Optional

import jwt

from app.config import get_settings
from app.database import next_id
from app.utils.errors import AppError
from app.utils.mongo import to_api
from app.utils.timeutil import utcnow

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ROLES = ("investigator", "admin")
_SCRYPT = dict(n=2 ** 14, r=8, p=1, dklen=32)


# ---- password hashing ------------------------------------------------------------------
def hash_password(password: str) -> str:
    try:
        from argon2 import PasswordHasher
        return PasswordHasher().hash(password)  # "$argon2id$..."
    except ImportError:
        salt = os.urandom(16)
        dk = hashlib.scrypt(password.encode(), salt=salt, maxmem=64 * 1024 * 1024, **_SCRYPT)
        return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        if stored.startswith("$argon2"):
            from argon2 import PasswordHasher
            return PasswordHasher().verify(stored, password)
        if stored.startswith("scrypt$"):
            _, salt_b64, dk_b64 = stored.split("$")
            dk = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt_b64),
                                maxmem=64 * 1024 * 1024, **_SCRYPT)
            return hmac.compare_digest(dk, base64.b64decode(dk_b64))
    except Exception:  # bad hash / argon2 VerifyMismatchError / missing argon2 for an argon2 hash
        return False
    return False


# ---- JWT --------------------------------------------------------------------------------
def create_access_token(user: dict) -> str:
    s = get_settings()
    now = utcnow()
    payload = {"sub": user["user_id"], "role": user["role"],
               "iat": now, "exp": now + timedelta(minutes=s.jwt_expire_minutes)}
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    s = get_settings()
    try:
        return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm], options={"require": ["exp", "sub"]})
    except jwt.ExpiredSignatureError:
        raise AppError(401, "TOKEN_EXPIRED", "Session expired. Please log in again.")
    except jwt.PyJWTError:
        raise AppError(401, "INVALID_TOKEN", "Invalid authentication token.")


def public_user(doc: dict) -> dict:
    out = to_api(doc)
    out.pop("password_hash", None)
    return out


# ---- accounts ---------------------------------------------------------------------------
def register(db, full_name: str, email: str, organization: str, password: str) -> dict:
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        raise AppError(422, "INVALID_EMAIL", "Email address is not valid.")
    if len(password) < 8:
        raise AppError(422, "WEAK_PASSWORD", "Password must be at least 8 characters.")
    if db.users.find_one({"email": email}):
        raise AppError(409, "EMAIL_EXISTS", "An account with this email already exists.")
    now = utcnow()
    doc = {"user_id": next_id(db, "user", "USR-ROCKET", 4), "full_name": full_name.strip(), "email": email,
           "organization": organization.strip(), "password_hash": hash_password(password),
           "role": "investigator",  # role is never taken from the request; promote admins directly in MongoDB
           "created_at": now, "updated_at": now}
    db.users.insert_one(dict(doc))
    return public_user(doc)


def login(db, email: str, password: str) -> dict:
    doc = db.users.find_one({"email": email.strip().lower()})
    if not doc or not verify_password(password, doc["password_hash"]):
        raise AppError(401, "INVALID_CREDENTIALS", "Incorrect email or password.")
    return {"access_token": create_access_token(doc), "token_type": "bearer", "user": public_user(doc)}


def get_user(db, user_id: str) -> Optional[dict]:
    return db.users.find_one({"user_id": user_id})

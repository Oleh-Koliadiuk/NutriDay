import secrets

import bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False

    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        try:
            if password_hash.startswith("$2"):
                return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
        except Exception:
            return False
        return False


def generate_token() -> str:
    return secrets.token_urlsafe(32)



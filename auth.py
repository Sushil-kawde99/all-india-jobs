import os
import hmac
import hashlib
import time
import base64
from typing import Optional, Dict, Any
import config

FAILED_ATTEMPTS = {}
COOKIE_NAME = "jobdisha_admin_token"

def check_rate_limit(client_ip: str) -> bool:
    now = time.time()
    record = FAILED_ATTEMPTS.get(client_ip)
    if record and record["locked_until"] > now:
        return False
    return True

def record_failed_attempt(client_ip: str) -> None:
    now = time.time()
    record = FAILED_ATTEMPTS.get(client_ip, {"count": 0, "locked_until": 0})
    record["count"] += 1
    if record["count"] >= 5:
        record["locked_until"] = now + 60
    FAILED_ATTEMPTS[client_ip] = record

def reset_attempts(client_ip: str) -> None:
    if client_ip in FAILED_ATTEMPTS:
        del FAILED_ATTEMPTS[client_ip]

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.strip().encode("utf-8"), salt, 120_000)
    return f"pbkdf2_sha256${salt.hex()}${dk.hex()}"

def verify_password_hash(password: str, stored_hash: str) -> bool:
    try:
        scheme, salt_hex, hash_hex = stored_hash.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = hashlib.pbkdf2_hmac("sha256", password.strip().encode("utf-8"), salt, 120_000).hex()
        return hmac.compare_digest(expected, hash_hex)
    except Exception:
        return False

def is_super_admin_credentials(username: str, password: str) -> bool:
    return hmac.compare_digest(username.strip(), config.ADMIN_USERNAME.strip()) and \
           hmac.compare_digest(password.strip(), config.ADMIN_PASSWORD.strip())

def authenticate_admin(username: str, password: str) -> Optional[Dict[str, Any]]:
    uname = username.strip()
    pwd = password.strip()
    if is_super_admin_credentials(uname, pwd):
        return {
            "username": config.ADMIN_USERNAME.strip(),
            "company_name": "All India Jobs (Super Admin)",
            "role": "super_admin",
            "can_view_all_jobs": 1,
            "can_add_jobs": 1,
            "is_active": 1,
        }

    import db
    user = db.get_admin_user_by_username(uname)
    if not user or user.get("is_active") != 1:
        return None
    if verify_password_hash(pwd, user.get("password_hash", "")):
        return user
    return None

def verify_credentials(username: str, password: str) -> bool:
    return authenticate_admin(username, password) is not None

def create_session_token(username: str) -> str:
    timestamp = str(int(time.time()))
    payload = f"{username.strip()}:{timestamp}"
    sig = hmac.new(config.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    raw = f"{payload}:{sig}"
    return base64.urlsafe_b64encode(raw.encode()).decode()

def get_session_username(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        parts = raw.split(":")
        if len(parts) != 3:
            return None
        user, ts_str, sig = parts
        expected_sig = hmac.new(config.SECRET_KEY.encode(), f"{user}:{ts_str}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        ts = int(ts_str)
        if time.time() - ts > 60 * 60 * 24 * 7:
            return None
        return user
    except Exception:
        return None

def verify_session_token(token: Optional[str]) -> bool:
    return get_session_admin(token) is not None

def get_session_admin(token: Optional[str]) -> Optional[Dict[str, Any]]:
    username = get_session_username(token)
    if not username:
        return None
    if hmac.compare_digest(username, config.ADMIN_USERNAME.strip()):
        return {
            "username": config.ADMIN_USERNAME.strip(),
            "company_name": "All India Jobs (Super Admin)",
            "role": "super_admin",
            "can_view_all_jobs": 1,
            "can_add_jobs": 1,
            "is_active": 1,
        }
    import db
    user = db.get_admin_user_by_username(username)
    if not user or user.get("is_active") != 1:
        return None
    return user

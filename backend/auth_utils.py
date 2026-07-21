# Authentication + authorization building blocks shared by every router.
# Password hashing (bcrypt), JWT issuing/verification, and the FastAPI
# dependencies (`get_current_user`, `require_role(...)`) that routes use
# via `Depends(...)` to enforce "must be logged in" / "must be this role".
# NOTE: this file only covers *authentication* (who is this?) and *role*
# checks (what kind of user are they?) — per-resource *ownership* checks
# (e.g. "is this teacher's course?") are done inline in each router instead.
import os
import jwt
import bcrypt
from datetime import datetime, timezone, timedelta
from fastapi import Request, HTTPException, Depends
from database import db

JWT_ALGORITHM = "HS256"


def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]


def hash_password(password: str) -> str:
    """One-way bcrypt hash for storing a new password — never store plaintext."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Check a login attempt's plaintext password against the stored bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, email: str, role: str) -> str:
    """Issue a signed JWT (7-day expiry) after successful login/register.
    `role` is embedded in the token itself, but get_current_user() always
    re-reads the live role from the database rather than trusting the
    token's copy — so a role change takes effect immediately, not after
    the old token expires."""
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "access",
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


async def get_current_user(request: Request) -> dict:
    """FastAPI dependency: extract + verify the caller's JWT and return
    their user document (password_hash stripped). Accepts the token from
    either the Authorization: Bearer header (what the frontend actually
    sends, via axios) or the access_token cookie (set on login/register as
    a fallback / for any non-SPA callers). Raises 401 for anything wrong —
    missing token, expired, tampered, or user since deleted."""
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": payload["sub"]})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user["id"] = user.pop("_id")  # normalize Mongo's _id to id for the rest of the app
        user.pop("password_hash", None)  # never leak the hash to route handlers/responses
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_role(*roles):
    """FastAPI dependency factory — use as Depends(require_role("teacher", "admin"))
    on any route that only certain roles may call. Runs get_current_user()
    first (so it also enforces "must be logged in"), then 403s if the
    user's role isn't in the allowed set."""
    async def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Not authorized for this action")
        return user
    return checker


async def optional_user(request: Request) -> dict | None:
    """Same as get_current_user but returns None if not authenticated instead
    of raising — used on routes that behave differently for logged-in vs.
    anonymous visitors (e.g. the public course list) rather than blocking
    anonymous access outright."""
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


# Fixed demo login accounts (seeded in seed.py). Used to gate "demo/preview"
# content — courses etc. created by the demo teacher are tagged demo_scope
# and only shown to the demo student or an admin, keeping public demos from
# polluting what real teachers/students see and vice versa.
DEMO_TEACHER_EMAIL = "teacher@bioexamprep.com"
DEMO_STUDENT_EMAIL = "student@bioexamprep.com"
DEMO_EMAILS = {DEMO_TEACHER_EMAIL, DEMO_STUDENT_EMAIL}


def is_demo_user(user: dict | None) -> bool:
    """Check the persisted `is_demo` flag with a fallback to email match (for pre-migration robustness)."""
    if not user:
        return False
    if user.get("is_demo") is True:
        return True
    return (user.get("email") or "").lower() in DEMO_EMAILS


def is_demo_teacher_email(email: str) -> bool:
    return (email or "").lower() == DEMO_TEACHER_EMAIL


async def demo_user_ids() -> list:
    """Return the list of user_ids currently flagged as demo (or matching demo emails)."""
    ids = []
    async for u in db.users.find({"$or": [{"is_demo": True}, {"email": {"$in": list(DEMO_EMAILS)}}]}, {"_id": 1}):
        ids.append(u["_id"])
    return ids


def can_see_demo_content(user: dict | None) -> bool:
    """Admin + demo student see demo content. Everyone else does not."""
    if not user:
        return False
    if user.get("role") == "admin":
        return True
    return (user.get("email") or "").lower() == DEMO_STUDENT_EMAIL

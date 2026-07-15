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
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "access",
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


async def get_current_user(request: Request) -> dict:
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
        user["id"] = user.pop("_id")
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_role(*roles):
    async def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Not authorized for this action")
        return user
    return checker


async def optional_user(request: Request) -> dict | None:
    """Same as get_current_user but returns None if not authenticated instead of raising."""
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


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

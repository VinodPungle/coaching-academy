import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel, EmailStr
from database import db
from auth_utils import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterBody(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "student"


class LoginBody(BaseModel):
    email: EmailStr
    password: str


def public_user(doc: dict) -> dict:
    return {
        "id": doc["_id"],
        "name": doc["name"],
        "email": doc["email"],
        "role": doc["role"],
    }


@router.post("/register")
async def register(body: RegisterBody, response: Response):
    if body.role not in ("student", "teacher"):
        raise HTTPException(status_code=400, detail="Role must be student or teacher")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    email = body.email.lower().strip()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    doc = {
        "_id": str(uuid.uuid4()),
        "name": body.name.strip(),
        "email": email,
        "password_hash": hash_password(body.password),
        "role": body.role,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    token = create_access_token(doc["_id"], email, body.role)
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=604800, path="/")
    return {"user": public_user(doc), "access_token": token}


@router.post("/login")
async def login(body: LoginBody, response: Response):
    email = body.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user["_id"], email, user["role"])
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=604800, path="/")
    return {"user": public_user(user), "access_token": token}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"message": "Logged out"}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user

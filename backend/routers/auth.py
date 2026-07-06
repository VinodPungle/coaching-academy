import os
import uuid
import secrets
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel, EmailStr
from database import db
from auth_utils import hash_password, verify_password, create_access_token, get_current_user
from notify import send_email, email_template

logger = logging.getLogger(__name__)

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


class ForgotPasswordBody(BaseModel):
    email: EmailStr


class ResetPasswordBody(BaseModel):
    token: str
    password: str


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordBody):
    email = body.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if user:
        token = secrets.token_urlsafe(32)
        await db.password_reset_tokens.insert_one({
            "_id": token,
            "user_id": user["_id"],
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "used": False,
        })
        link = f"{os.environ.get('FRONTEND_URL', '')}/reset-password?token={token}"
        logger.info(f"Password reset link for {email}: {link}")
        asyncio.create_task(send_email(
            email,
            "Reset your JAM Academy password",
            email_template(
                "Reset your password",
                f"Hi {user['name']},<br/><br/>We received a request to reset your JAM Academy password. Click the button below to choose a new one. This link expires in 1 hour.<br/><br/>If you didn't request this, you can safely ignore this email.",
                "Reset password",
                link,
            ),
        ))
    return {"message": "If an account exists for this email, a password reset link has been sent."}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordBody):
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    rec = await db.password_reset_tokens.find_one({"_id": body.token})
    if not rec or rec.get("used"):
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    exp = rec["expires_at"]
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    await db.users.update_one({"_id": rec["user_id"]}, {"$set": {"password_hash": hash_password(body.password)}})
    await db.password_reset_tokens.update_one({"_id": body.token}, {"$set": {"used": True}})
    return {"message": "Password reset successful. You can now log in with your new password."}

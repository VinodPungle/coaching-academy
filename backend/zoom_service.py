import os
import time
import base64
import httpx
from fastapi import HTTPException

_token_cache = {"token": None, "exp": 0}


def zoom_configured() -> bool:
    return all(os.environ.get(k, "").strip() for k in ("ZOOM_ACCOUNT_ID", "ZOOM_CLIENT_ID", "ZOOM_CLIENT_SECRET"))


async def get_zoom_token() -> str:
    if _token_cache["token"] and time.time() < _token_cache["exp"]:
        return _token_cache["token"]
    url = f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={os.environ['ZOOM_ACCOUNT_ID']}"
    b64 = base64.b64encode(f"{os.environ['ZOOM_CLIENT_ID']}:{os.environ['ZOOM_CLIENT_SECRET']}".encode()).decode()
    async with httpx.AsyncClient() as client:
        res = await client.post(url, headers={"Authorization": f"Basic {b64}"})
    if res.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to authenticate with Zoom. Check your Zoom credentials.")
    data = res.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["exp"] = time.time() + data.get("expires_in", 3600) - 60
    return _token_cache["token"]


async def create_zoom_meeting(topic: str, start_time_iso: str, duration_min: int) -> dict:
    token = await get_zoom_token()
    payload = {
        "topic": topic,
        "type": 2,
        "start_time": start_time_iso,
        "duration": duration_min,
        "timezone": "UTC",
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://api.zoom.us/v2/users/me/meetings",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
    if res.status_code != 201:
        raise HTTPException(status_code=502, detail=f"Zoom meeting creation failed: {res.text[:200]}")
    return res.json()

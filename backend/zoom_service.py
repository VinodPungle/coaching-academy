# Thin wrapper around Zoom's Server-to-Server OAuth API, used by
# routers/live_classes.py to auto-create a Zoom meeting when a teacher
# schedules a live class (instead of requiring them to paste a manual link).
import os
import time
import base64
import httpx
from fastapi import HTTPException

# Cached access token (Zoom tokens are short-lived; re-fetching on every
# request would be wasteful and slow). Module-level dict = simple in-process
# cache, fine because there's only one backend process per container.
_token_cache = {"token": None, "exp": 0}


def zoom_configured() -> bool:
    """True only if all three Zoom S2S OAuth env vars are set — callers use
    this to fall back to manual meeting links when Zoom isn't configured."""
    return all(os.environ.get(k, "").strip() for k in ("ZOOM_ACCOUNT_ID", "ZOOM_CLIENT_ID", "ZOOM_CLIENT_SECRET"))


async def get_zoom_token() -> str:
    """Return a valid OAuth access token, reusing the cached one until ~1 min
    before it expires; otherwise requests a fresh one via Zoom's
    account_credentials grant (Server-to-Server OAuth, no user login flow)."""
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
    _token_cache["exp"] = time.time() + data.get("expires_in", 3600) - 60  # refresh 60s early
    return _token_cache["token"]


async def create_zoom_meeting(topic: str, start_time_iso: str, duration_min: int) -> dict:
    """Create a scheduled Zoom meeting (type=2) under the connected Zoom
    account and return Zoom's raw meeting object (join_url, id, etc.) for
    the caller to store on the live_classes document."""
    token = await get_zoom_token()
    payload = {
        "topic": topic,
        "type": 2,  # 2 = scheduled meeting (vs. 1 = instant, 3 = recurring no fixed time)
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

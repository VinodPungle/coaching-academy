"""
Persistent object-storage wrapper (Emergent-managed).

Provides put_object() and get_object() with a session-scoped storage_key
initialised once at process startup. Falls back gracefully if EMERGENT_LLM_KEY
is not configured (raises RuntimeError so callers can surface a friendly error).
"""
import os
import logging
import requests

logger = logging.getLogger(__name__)

STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
APP_NAME = "bioexamprep"

_storage_key: str | None = None


def is_configured() -> bool:
    return bool(os.environ.get("EMERGENT_LLM_KEY"))


def init_storage() -> str:
    """Initialise session-scoped storage_key. Call once at startup."""
    global _storage_key
    if _storage_key:
        return _storage_key
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise RuntimeError("EMERGENT_LLM_KEY is not set — object storage is unavailable.")
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": key}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def _key_or_reinit() -> str:
    global _storage_key
    if _storage_key:
        return _storage_key
    return init_storage()


def put_object(path: str, data: bytes, content_type: str) -> dict:
    """Upload bytes to `path`. Returns {"path": ..., "size": ..., "etag": ...}.
    Retries once with a fresh storage_key on 403.
    """
    global _storage_key
    key = _key_or_reinit()
    for attempt in range(2):
        resp = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type or "application/octet-stream"},
            data=data,
            timeout=180,
        )
        if resp.status_code == 403 and attempt == 0:
            _storage_key = None
            key = init_storage()
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError("Object storage put_object failed after re-init")


def get_object(path: str) -> tuple[bytes, str]:
    """Download the object at `path`. Returns (bytes, content_type)."""
    global _storage_key
    key = _key_or_reinit()
    for attempt in range(2):
        resp = requests.get(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key},
            timeout=120,
        )
        if resp.status_code == 403 and attempt == 0:
            _storage_key = None
            key = init_storage()
            continue
        resp.raise_for_status()
        return resp.content, resp.headers.get("Content-Type", "application/octet-stream")
    raise RuntimeError("Object storage get_object failed after re-init")


def build_path(user_id: str, file_id: str, ext: str) -> str:
    ext = (ext or "").lstrip(".") or "bin"
    return f"{APP_NAME}/uploads/{user_id}/{file_id}.{ext}"

"""
Object-storage wrapper.

Backends, chosen by environment:
  1. Azure Blob Storage — when AZURE_STORAGE_CONNECTION_STRING is set
     (container name from AZURE_STORAGE_CONTAINER, default "uploads").
  2. Local disk — fallback for development; files land in backend/uploads/.

Public API used by routers: is_configured(), build_path(),
put_object(), get_object(), delete_object().
"""
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

APP_NAME = "bioexamprep"
LOCAL_STORAGE_DIR = Path(__file__).parent / "uploads"

_container_client = None


def _azure_connection_string() -> str:
    return os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "").strip()


def is_configured() -> bool:
    # Always true: Azure Blob when configured, local disk otherwise.
    return True


def _get_container():
    """Lazily build (and cache) the Azure container client."""
    global _container_client
    if _container_client is not None:
        return _container_client
    from azure.storage.blob import BlobServiceClient  # imported lazily — not needed for local disk

    service = BlobServiceClient.from_connection_string(_azure_connection_string())
    container_name = os.environ.get("AZURE_STORAGE_CONTAINER", "uploads")
    container = service.get_container_client(container_name)
    if not container.exists():
        container.create_container()
    _container_client = container
    return container


def put_object(path: str, data: bytes, content_type: str) -> dict:
    """Store bytes at `path`. Returns {"path": ..., "size": ...}."""
    if _azure_connection_string():
        from azure.storage.blob import ContentSettings

        blob = _get_container().get_blob_client(path)
        blob.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type or "application/octet-stream"),
        )
        return {"path": path, "size": len(data)}

    target = LOCAL_STORAGE_DIR / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return {"path": path, "size": len(data)}


def get_object(path: str) -> tuple[bytes, str]:
    """Fetch the object at `path`. Returns (bytes, content_type)."""
    if _azure_connection_string():
        blob = _get_container().get_blob_client(path)
        downloader = blob.download_blob()
        props = downloader.properties
        content_type = getattr(getattr(props, "content_settings", None), "content_type", None)
        return downloader.readall(), content_type or "application/octet-stream"

    target = LOCAL_STORAGE_DIR / path
    if not target.exists():
        raise FileNotFoundError(f"Object not found: {path}")
    return target.read_bytes(), "application/octet-stream"


def delete_object(path: str) -> None:
    """Remove the object at `path`. Best-effort: a missing object is not an error."""
    if _azure_connection_string():
        blob = _get_container().get_blob_client(path)
        try:
            blob.delete_blob()
        except Exception as exc:  # noqa: BLE001 — cleanup must not block the caller
            logger.warning("Failed to delete blob %s: %s", path, exc)
        return

    target = LOCAL_STORAGE_DIR / path
    try:
        if target.exists():
            target.unlink()
    except OSError as exc:
        logger.warning("Failed to delete local object %s: %s", path, exc)


def build_path(user_id: str, file_id: str, ext: str) -> str:
    ext = (ext or "").lstrip(".") or "bin"
    return f"{APP_NAME}/uploads/{user_id}/{file_id}.{ext}"

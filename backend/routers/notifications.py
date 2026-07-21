# In-app notification inbox (the bell icon — see NotificationsBell.jsx).
# The notifications themselves are created by notify.py's notify() helper
# from other routers; this file only reads/marks them for the current user.
from fastapi import APIRouter, Depends
from database import db
from auth_utils import get_current_user

router = APIRouter(tags=["notifications"])


@router.get("/notifications")
async def list_notifications(user: dict = Depends(get_current_user)):
    """Most recent 30 notifications for the caller, plus their total unread count."""
    docs = await db.notifications.find({"user_id": user["id"]}).sort("created_at", -1).to_list(30)
    for d in docs:
        d["id"] = d.pop("_id")
    unread = await db.notifications.count_documents({"user_id": user["id"], "read": False})
    return {"items": docs, "unread": unread}


@router.post("/notifications/read-all")
async def mark_all_read(user: dict = Depends(get_current_user)):
    """Bulk-marks every unread notification for the caller as read (e.g. on
    opening the notification dropdown)."""
    await db.notifications.update_many({"user_id": user["id"], "read": False}, {"$set": {"read": True}})
    return {"message": "All notifications marked read"}

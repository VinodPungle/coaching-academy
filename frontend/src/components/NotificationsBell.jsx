// Bell icon + dropdown mounted in PortalLayout, present on every /app/*
// page. Also doubles as the UI for opting into WhatsApp notifications
// (saves a phone number via PUT /auth/profile — see notify.py for how
// that number then gets used).
import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Bell, CheckCheck, MessageCircle } from "lucide-react";
import dayjs from "dayjs";

export const NotificationsBell = () => {
  const [data, setData] = useState({ items: [], unread: 0 });
  const [open, setOpen] = useState(false);
  const { user } = useAuth();
  const [phone, setPhone] = useState(user?.phone || "");
  const navigate = useNavigate();

  const savePhone = async () => {
    try {
      await api.put("/auth/profile", { phone });
      toast.success(phone ? "WhatsApp number saved" : "WhatsApp number removed");
    } catch (e) {
      toast.error(formatApiError(e));
    }
  };

  const load = useCallback(() => {
    api.get("/notifications").then((r) => setData(r.data)).catch(() => {});
  }, []);

  // Poll every 30s — simplest way to approximate "live" notifications
  // without adding websockets, acceptable given the notification volume
  // this app generates.
  useEffect(() => {
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, [load]);

  const markAllRead = async () => {
    await api.post("/notifications/read-all");
    load();
  };

  const openItem = (n) => {
    setOpen(false);
    if (n.link) navigate(n.link);
  };

  return (
    <>
      <button
        onClick={() => setOpen(!open)}
        data-testid="notifications-bell"
        className="fixed z-40 top-2.5 right-20 md:top-5 md:right-8 p-2.5 bg-white border border-zinc-200 hover:border-zinc-400 transition-colors shadow-sm"
        title="Notifications"
      >
        <Bell className="w-4 h-4 text-zinc-700" />
        {data.unread > 0 && (
          <span data-testid="notifications-unread-badge" className="absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] px-1 bg-red-600 text-white text-[10px] font-bold flex items-center justify-center">
            {data.unread > 9 ? "9+" : data.unread}
          </span>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div data-testid="notifications-panel" className="fixed z-50 top-14 right-2 md:top-16 md:right-8 w-[340px] max-w-[calc(100vw-16px)] bg-white border border-zinc-200 shadow-xl">
            <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-200">
              <span className="font-heading font-bold text-sm">Notifications</span>
              {data.unread > 0 && (
                <button onClick={markAllRead} data-testid="mark-all-read-button" className="inline-flex items-center gap-1 text-xs font-semibold text-blue-700 hover:underline">
                  <CheckCheck className="w-3.5 h-3.5" /> Mark all read
                </button>
              )}
            </div>
            <div className="max-h-[380px] overflow-y-auto">
              {data.items.length === 0 && <p className="px-4 py-8 text-sm text-zinc-500 text-center" data-testid="notifications-empty">No notifications yet.</p>}
              {data.items.map((n) => (
                <button
                  key={n.id}
                  onClick={() => openItem(n)}
                  data-testid={`notification-item-${n.id}`}
                  className={`w-full text-left px-4 py-3 border-b border-zinc-100 last:border-0 hover:bg-zinc-50 transition-colors ${!n.read ? "bg-blue-50/60" : ""}`}
                >
                  <div className="flex items-start gap-2">
                    {!n.read && <span className="mt-1.5 w-1.5 h-1.5 bg-blue-700 shrink-0" />}
                    <div className="min-w-0">
                      <p className="text-sm font-semibold leading-snug">{n.title}</p>
                      <p className="text-xs text-zinc-500 mt-0.5 line-clamp-2">{n.body}</p>
                      <p className="text-[10px] uppercase tracking-[0.1em] text-zinc-400 mt-1">{dayjs(n.created_at).format("D MMM, h:mm A")}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
            <div className="border-t border-zinc-200 px-4 py-3 bg-zinc-50">
              <p className="text-[10px] uppercase tracking-[0.15em] font-semibold text-zinc-500 flex items-center gap-1.5">
                <MessageCircle className="w-3.5 h-3.5 text-green-600" /> Get these on WhatsApp
              </p>
              <div className="mt-2 flex gap-2">
                <input
                  data-testid="whatsapp-phone-input"
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+919876543210"
                  className="flex-1 border border-zinc-300 px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-700"
                />
                <button onClick={savePhone} data-testid="whatsapp-phone-save" className="px-3 py-1.5 text-xs font-semibold bg-blue-700 text-white hover:bg-blue-900 transition-colors">
                  Save
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
};

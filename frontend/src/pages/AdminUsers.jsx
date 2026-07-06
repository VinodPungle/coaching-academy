import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/context/AuthContext";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Search, Trash2 } from "lucide-react";
import dayjs from "dayjs";

export default function AdminUsers() {
  const { user } = useAuth();
  const [users, setUsers] = useState([]);
  const [q, setQ] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(null);

  const load = useCallback(() => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (roleFilter) params.set("role", roleFilter);
    api.get(`/admin/users?${params}`).then((r) => setUsers(r.data));
  }, [q, roleFilter]);

  useEffect(() => {
    const t = setTimeout(load, 300);
    return () => clearTimeout(t);
  }, [load]);

  const changeRole = async (id, role) => {
    try {
      await api.put(`/admin/users/${id}/role`, { role });
      toast.success("Role updated");
      load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  };

  const remove = async (id) => {
    try {
      await api.delete(`/admin/users/${id}`);
      toast.success("User deleted");
      setConfirmDelete(null);
      load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="font-heading text-3xl font-black tracking-tight">Users</h1>
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-56 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
          <input
            data-testid="admin-users-search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search name or email…"
            className="w-full border border-zinc-300 pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700"
          />
        </div>
        <select data-testid="admin-users-role-filter" value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)} className="border border-zinc-300 px-3 py-2 text-sm bg-white">
          <option value="">All roles</option>
          <option value="student">Students</option>
          <option value="teacher">Teachers</option>
          <option value="admin">Admins</option>
        </select>
      </div>

      <div className="border border-zinc-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-zinc-50 text-left text-xs uppercase tracking-[0.1em] text-zinc-500">
            <tr>
              <th className="px-5 py-3 font-semibold">Name</th>
              <th className="px-5 py-3 font-semibold">Email</th>
              <th className="px-5 py-3 font-semibold">Role</th>
              <th className="px-5 py-3 font-semibold">Joined</th>
              <th className="px-5 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-t border-zinc-100" data-testid={`admin-user-row-${u.id}`}>
                <td className="px-5 py-3 font-medium">{u.name}{u.id === user.id && <span className="text-xs text-zinc-400 ml-1">(you)</span>}</td>
                <td className="px-5 py-3 text-zinc-500">{u.email}</td>
                <td className="px-5 py-3">
                  <select
                    data-testid={`admin-role-select-${u.id}`}
                    value={u.role}
                    disabled={u.id === user.id}
                    onChange={(e) => changeRole(u.id, e.target.value)}
                    className="border border-zinc-300 px-2 py-1 text-xs font-semibold bg-white disabled:opacity-50"
                  >
                    <option value="student">student</option>
                    <option value="teacher">teacher</option>
                    <option value="admin">admin</option>
                  </select>
                </td>
                <td className="px-5 py-3 text-zinc-500">{u.created_at ? dayjs(u.created_at).format("D MMM YYYY") : "—"}</td>
                <td className="px-5 py-3 text-right">
                  {confirmDelete === u.id ? (
                    <span className="inline-flex gap-2">
                      <button onClick={() => remove(u.id)} data-testid={`confirm-delete-${u.id}`} className="text-xs font-bold text-red-600 hover:underline">Confirm</button>
                      <button onClick={() => setConfirmDelete(null)} className="text-xs text-zinc-400 hover:underline">Cancel</button>
                    </span>
                  ) : (
                    <button
                      onClick={() => setConfirmDelete(u.id)}
                      disabled={u.id === user.id}
                      data-testid={`admin-delete-user-${u.id}`}
                      className="p-1.5 text-zinc-400 hover:text-red-600 disabled:opacity-30"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {users.length === 0 && <p className="px-5 py-8 text-sm text-zinc-500" data-testid="admin-users-empty">No users found.</p>}
      </div>
    </div>
  );
}

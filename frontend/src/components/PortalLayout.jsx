import { NavLink, useNavigate, Outlet } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { NotificationsBell } from "@/components/NotificationsBell";
import {
  LayoutDashboard, BookOpen, Radio, FileQuestion, ClipboardList, Megaphone, LogOut, GraduationCap,
} from "lucide-react";

const NAV = [
  { to: "/app/dashboard", label: "Dashboard", icon: LayoutDashboard, testid: "nav-dashboard" },
  { to: "/app/courses", label: "Courses", icon: BookOpen, testid: "nav-courses" },
  { to: "/app/live", label: "Live Classes", icon: Radio, testid: "nav-live-classes" },
  { to: "/app/tests", label: "Tests", icon: FileQuestion, testid: "nav-tests" },
  { to: "/app/assignments", label: "Assignments", icon: ClipboardList, testid: "nav-assignments" },
  { to: "/app/announcements", label: "Announcements", icon: Megaphone, testid: "nav-announcements" },
];

export default function PortalLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  return (
    <div className="flex min-h-screen bg-white text-zinc-950">
      <aside className="hidden md:flex w-60 flex-col border-r border-zinc-200 bg-zinc-50 fixed inset-y-0">
        <div className="flex items-center gap-2 px-5 h-16 border-b border-zinc-200">
          <GraduationCap className="w-6 h-6 text-blue-700" />
          <span className="font-heading font-black tracking-tight text-lg">JAM Academy</span>
        </div>
        <nav className="flex-1 py-4 space-y-0.5">
          {NAV.map(({ to, label, icon: Icon, testid }) => (
            <NavLink
              key={to}
              to={to}
              data-testid={testid}
              className={({ isActive }) =>
                `flex items-center gap-3 px-5 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-blue-700 text-white"
                    : "text-zinc-600 hover:bg-zinc-200 hover:text-zinc-950"
                }`
              }
            >
              <Icon className="w-4 h-4" strokeWidth={2} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-zinc-200 p-4">
          <div className="text-sm font-semibold truncate" data-testid="sidebar-user-name">{user?.name}</div>
          <div className="text-xs uppercase tracking-[0.15em] text-zinc-500 mt-0.5" data-testid="sidebar-user-role">{user?.role}</div>
          <button
            onClick={handleLogout}
            data-testid="logout-button"
            className="mt-3 flex w-full items-center gap-2 border border-zinc-300 bg-white px-3 py-2 text-sm font-medium hover:bg-zinc-100 transition-colors"
          >
            <LogOut className="w-4 h-4" /> Log out
          </button>
        </div>
      </aside>

      <div className="md:hidden fixed top-0 inset-x-0 z-40 flex items-center justify-between border-b border-zinc-200 bg-white/80 backdrop-blur-xl px-4 h-14">
        <span className="font-heading font-black">JAM Academy</span>
        <button onClick={handleLogout} data-testid="mobile-logout-button" className="text-sm font-medium text-zinc-600">
          Log out
        </button>
      </div>
      <div className="md:hidden fixed bottom-0 inset-x-0 z-40 flex border-t border-zinc-200 bg-white">
        {NAV.map(({ to, icon: Icon }) => (
          <NavLink key={to} to={to} className={({ isActive }) => `flex-1 flex justify-center py-3 ${isActive ? "text-blue-700" : "text-zinc-400"}`}>
            <Icon className="w-5 h-5" />
          </NavLink>
        ))}
      </div>

      <main className="flex-1 md:ml-60 pt-14 md:pt-0 pb-16 md:pb-0">
        <NotificationsBell />
        <div className="p-4 md:p-8 max-w-6xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

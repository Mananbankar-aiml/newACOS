import React from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import {
  LayoutDashboard,
  Bot,
  Users,
  Wallet,
  Boxes,
  LineChart,
  ScrollText,
  BarChart3,
  ShieldCheck,
  History,
  SlidersHorizontal,
} from "lucide-react";

const items = [
  { to: "/",            title: "Dashboard",  icon: LayoutDashboard },
  { to: "/agents",      title: "Agents",     icon: Bot },
  { to: "/hr",          title: "HR",         icon: Users },
  { to: "/finance",     title: "Finance",    icon: Wallet,          employeeHidden: true },
  { to: "/inventory",   title: "Inventory",  icon: Boxes },
  { to: "/sales",       title: "Sales",      icon: LineChart,       employeeHidden: true },
  { to: "/compliance",  title: "Compliance", icon: ShieldCheck,     employeeHidden: true },
  { to: "/analytics",   title: "Analytics",  icon: BarChart3 },
  { to: "/approvals",   title: "Approvals",  icon: ScrollText,      employeeHidden: true },
  { to: "/audit-logs",  title: "Audit",      icon: History,         adminManagerOnly: true },
  { to: "/settings",    title: "Settings",   icon: SlidersHorizontal },
];

export default function GradientMenu() {
  const { user } = useAuth();
  const restricted = user?.role === "employee" || user?.role === "pending";
  const role = user?.role;
  const visibleItems = items.filter((it) => {
    if (restricted && it.employeeHidden) return false;
    if (it.adminManagerOnly && role !== "admin" && role !== "manager") return false;
    return true;
  });
  return (
    <ul
      data-testid="gradient-menu"
      className="flex flex-nowrap gap-1 items-center justify-center px-2 py-2 rounded-[10px] border border-[#2a2a2e] bg-[#141416] w-fit mx-auto"
    >
      {visibleItems.map(({ to, title, icon: Icon }) => (
        <li key={to} className="relative shrink-0">
          <NavLink
            to={to}
            end={to === "/"}
            data-testid={`nav-${title.toLowerCase()}`}
            className={({ isActive }) =>
              `relative flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] transition-all duration-200 text-[11px] font-semibold uppercase tracking-wider ${
                isActive
                  ? "bg-[#29292d] text-[#f7f7f8]"
                  : "text-[#8c8c93] hover:bg-[#1c1c1f] hover:text-[#f7f7f8]"
              }`
            }
          >
            <Icon className="h-[15px] w-[15px] shrink-0" />
            <span className="whitespace-nowrap">{title}</span>
          </NavLink>
        </li>
      ))}
    </ul>
  );
}

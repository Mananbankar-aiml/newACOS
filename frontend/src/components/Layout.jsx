import React from "react";
import { Outlet, useNavigate } from "react-router-dom";
import GradientMenu from "@/components/ui/gradient-menu";
import MotionFooter from "@/components/ui/motion-footer";
import { useAuth } from "@/context/AuthContext";
import { LogOut } from "lucide-react";

export default function Layout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();

  return (
    <div className="min-h-screen bg-[#060607] text-[#f7f7f8]">
      {/* Top bar */}
      <header className="sticky top-0 z-50 w-full px-4 md:px-8 py-4 bg-[#060607] border-b border-[#2a2a2e]">
        <div className="max-w-[1400px] mx-auto flex items-center gap-6 justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="w-8 h-8 rounded-[6px] bg-[#a8a8ad] flex items-center justify-center">
              <div className="w-3.5 h-3.5 bg-[#17171a] rounded-sm" />
            </div>
            <div>
              <div className="font-display font-bold text-base leading-none tracking-tight text-[#f7f7f8]">ACOS</div>
              <div className="text-[10px] uppercase tracking-[0.25em] text-[#6f6f76] font-mono-i mt-0.5">Command Center</div>
            </div>
          </div>

          {/* Navigation */}
          <div className="hidden lg:block flex-1">
            <div className="flex justify-center">
              <GradientMenu />
            </div>
          </div>

          {/* User / logout */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="hidden md:flex items-center gap-3 pl-3 pr-2 py-1.5 rounded-[10px] border border-[#2a2a2e] bg-[#141416]">
              {user?.avatar ? (
                <img src={user.avatar} alt="" className="w-7 h-7 rounded-full object-cover" />
              ) : (
                <div className="w-7 h-7 rounded-full bg-[#29292d] flex items-center justify-center text-[#a8a8ad] text-xs font-bold">
                  {user?.name?.[0] ?? "U"}
                </div>
              )}
              <div className="pr-1">
                <div className="text-xs font-semibold text-[#f7f7f8] leading-tight">{user?.name}</div>
                <div className="text-[10px] uppercase tracking-widest text-[#6f6f76] font-mono-i">{user?.role}</div>
              </div>
            </div>
            <button
              onClick={() => { logout(); nav("/login"); }}
              data-testid="logout-btn"
              className="p-2 rounded-[6px] border border-[#2a2a2e] bg-[#141416] text-[#8c8c93] hover:text-[#f7f7f8] hover:bg-[#29292d] transition-colors"
              aria-label="Log out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        <div className="lg:hidden mt-4 overflow-x-auto pb-2 -mx-4 px-4 [&::-webkit-scrollbar]:hidden">
          <GradientMenu />
        </div>
      </header>

      <main className="relative z-10 max-w-[1400px] mx-auto px-4 md:px-8 py-8">
        {user?.role === "pending" && (
          <div data-testid="pending-banner" className="mb-6 p-4 rounded-[10px] border border-[#e2726f]/30 bg-[#e2726f]/5 text-sm text-[#f7f7f8]">
            Your account is <span className="font-bold">awaiting role assignment</span>. Your admin will grant access from Settings → Team &amp; Roles. Once assigned, refresh the page.
          </div>
        )}
        {user && !user.email_verified && user.auth_provider !== "google" && (
          <div data-testid="verify-banner" className="mb-6 p-4 rounded-[10px] border border-[#e2726f]/30 bg-[#e2726f]/5 flex items-center justify-between gap-4">
            <div className="text-sm text-[#f7f7f8]">
              Your email <span className="font-mono-i">{user.email}</span> hasn't been verified yet.
            </div>
            <a href="/verify" className="px-4 py-1.5 rounded-[6px] bg-[#a8a8ad] text-[#17171a] text-xs font-bold uppercase tracking-widest hover:bg-[#f7f7f8] transition-colors">
              Verify now
            </a>
          </div>
        )}
        <Outlet />
      </main>

      <MotionFooter />
    </div>
  );
}

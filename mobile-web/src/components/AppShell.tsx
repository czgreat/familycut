import { Outlet, useLocation } from "react-router-dom";

import { BottomNav } from "./BottomNav";
import { InstallBanner } from "./InstallBanner";
import { useAuth } from "../lib/auth";

export function AppShell() {
  const { member } = useAuth();
  const location = useLocation();
  const showNav = !location.pathname.startsWith("/profile/setup");

  return (
    <div className="app-shell">
      <div className="app-backdrop" />
      <header className="app-topbar">
        <div>
          <p className="app-topbar-kicker">FamilyCut</p>
          <strong>{member?.display_name ?? "移动端"}</strong>
        </div>
        <p className="app-topbar-meta">{member ? member.username : "未登录"}</p>
      </header>
      <main className="app-main">
        <InstallBanner />
        <Outlet />
      </main>
      {showNav ? <BottomNav /> : null}
    </div>
  );
}

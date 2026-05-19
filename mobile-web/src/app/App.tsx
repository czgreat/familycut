import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";

import { AppShell } from "../components/AppShell";
import { useAuth, isProfileComplete } from "../lib/auth";
import { HomePage } from "../pages/HomePage";
import { JoinPage } from "../pages/JoinPage";
import { LoginPage } from "../pages/LoginPage";
import { MealsPage } from "../pages/MealsPage";
import { ProfileSetupPage } from "../pages/ProfileSetupPage";
import { ReportDetailPage } from "../pages/ReportDetailPage";
import { ReportsPage } from "../pages/ReportsPage";
import { SettingsPage } from "../pages/SettingsPage";
import { WeightPage } from "../pages/WeightPage";

function BootScreen() {
  return (
    <main className="auth-shell">
      <section className="auth-card">
        <p className="screen-eyebrow">FamilyCut</p>
        <h1>正在恢复移动端会话…</h1>
        <p className="screen-subtitle">会先校验登录态，再决定是否跳转到资料补全。</p>
      </section>
    </main>
  );
}

function GuardedOutlet() {
  const { session, member, booting } = useAuth();
  const location = useLocation();

  if (booting) {
    return <BootScreen />;
  }

  if (!session?.accessToken) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (!member) {
    return <BootScreen />;
  }

  if (!isProfileComplete(member) && location.pathname !== "/profile/setup") {
    return <Navigate to="/profile/setup" replace />;
  }

  return <Outlet />;
}

function PublicOnly({ children }: { children: ReactNode }) {
  const { session, booting } = useAuth();
  if (booting) {
    return <BootScreen />;
  }
  if (session?.accessToken) {
    return <Navigate to="/home" replace />;
  }
  return <>{children}</>;
}

export function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <Routes>
        <Route
          path="/login"
          element={
            <PublicOnly>
              <LoginPage />
            </PublicOnly>
          }
        />
        <Route
          path="/join/:code"
          element={
            <PublicOnly>
              <JoinPage />
            </PublicOnly>
          }
        />
        <Route element={<GuardedOutlet />}>
          <Route element={<AppShell />}>
            <Route path="/home" element={<HomePage />} />
            <Route path="/weight" element={<WeightPage />} />
            <Route path="/meals" element={<MealsPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/reports/daily/:date" element={<ReportDetailPage kind="daily" />} />
            <Route path="/reports/weekly/:startDate" element={<ReportDetailPage kind="weekly" />} />
            <Route path="/reports/monthly/:yearMonth" element={<ReportDetailPage kind="monthly" />} />
            <Route path="/profile/setup" element={<ProfileSetupPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Route>
        <Route path="/" element={<Navigate to="/home" replace />} />
        <Route path="*" element={<Navigate to="/home" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

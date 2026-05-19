import { useEffect, useState } from "react";

import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { MembersPage } from "./pages/MembersPage";
import { SettingsPage } from "./pages/SettingsPage";
import { fetchCurrentMember, loginAdmin, MemberProfile } from "./lib/api";

type TabId = "dashboard" | "members" | "settings";

const tabs: Array<{ id: TabId; label: string }> = [
  { id: "dashboard", label: "概览" },
  { id: "members", label: "成员" },
  { id: "settings", label: "设置" }
];

const tokenStorageKey = "familycut_admin_token";

export function App() {
  const [activeTab, setActiveTab] = useState<TabId>("dashboard");
  const [token, setToken] = useState<string>(() => window.localStorage.getItem(tokenStorageKey) ?? "");
  const [currentMember, setCurrentMember] = useState<MemberProfile | null>(null);
  const [booting, setBooting] = useState(true);
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState("");
  const [authSuccess, setAuthSuccess] = useState("");

  useEffect(() => {
    if (!token) {
      setCurrentMember(null);
      setBooting(false);
      return;
    }

    setBooting(true);
    fetchCurrentMember(token)
      .then((member) => {
        if (member.role !== "admin") {
          throw new Error("只有管理员可以登录后台。");
        }
        setCurrentMember(member);
        setAuthError("");
        setAuthSuccess(`登录成功，当前管理员：${member.display_name}`);
      })
      .catch((error) => {
        window.localStorage.removeItem(tokenStorageKey);
        setToken("");
        setCurrentMember(null);
        setAuthError(error instanceof Error ? error.message : "登录状态已失效，请重新登录。");
        setAuthSuccess("");
      })
      .finally(() => setBooting(false));
  }, [token]);

  async function handleLogin(username: string, password: string) {
    setAuthBusy(true);
    setAuthError("");
    setAuthSuccess("");
    try {
      const payload = await loginAdmin(username, password);
      window.localStorage.setItem(tokenStorageKey, payload.tokens.access_token);
      setToken(payload.tokens.access_token);
      setAuthSuccess(`登录成功，欢迎 ${payload.display_name}`);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "登录失败。");
    } finally {
      setAuthBusy(false);
    }
  }

  function handleLogout() {
    window.localStorage.removeItem(tokenStorageKey);
    setToken("");
    setCurrentMember(null);
    setAuthError("");
    setAuthSuccess("已退出登录。");
  }

  if (booting) {
    return (
      <main className="login-shell">
        <section className="login-card">
          <p className="eyebrow">FamilyCut</p>
          <h1>正在校验管理员身份...</h1>
        </section>
      </main>
    );
  }

  if (!token || !currentMember) {
    return <LoginPage busy={authBusy} error={authError} success={authSuccess} onLogin={handleLogin} />;
  }

  let content = <DashboardPage token={token} />;
  if (activeTab === "members") {
    content = <MembersPage token={token} />;
  }
  if (activeTab === "settings") {
    content = <SettingsPage token={token} />;
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <p className="eyebrow">FamilyCut</p>
          <h1>家庭减脂后台</h1>
          <p>当前已登录：{currentMember.display_name}</p>
        </div>
        <div className="sidebar-status">
          <strong>{currentMember.username}</strong>
          <span>{currentMember.role === "admin" ? "管理员会话" : "成员会话"}</span>
        </div>
        <nav className="nav">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={tab.id === activeTab ? "nav-button nav-button-active" : "nav-button"}
              onClick={() => setActiveTab(tab.id)}
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-actions">
          <button className="nav-button" type="button" onClick={handleLogout}>
            退出登录
          </button>
        </div>
      </aside>
      <main className="content">
        <header className="content-topbar">
          <div>
            <p className="eyebrow">Control Center</p>
            <h2 className="content-title">
              {activeTab === "dashboard" ? "概览总控台" : activeTab === "members" ? "成员与邀请码" : "AI 与通知设置"}
            </h2>
            <p className="content-copy">保持配置、成员数据和日报链路都在一个统一后台里完成。</p>
          </div>
          <div className="content-meta-card">
            <span>当前仓库 FamilyCut</span>
            <strong>{currentMember.display_name}</strong>
          </div>
        </header>
        {authSuccess ? <p className="status-line status-success page-banner">{authSuccess}</p> : null}
        {content}
      </main>
    </div>
  );
}

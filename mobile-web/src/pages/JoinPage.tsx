import { FormEvent, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { previewInvite, registerByInvite } from "../lib/api";
import { useAuth } from "../lib/auth";

export function JoinPage() {
  const { code = "" } = useParams();
  const navigate = useNavigate();
  const { acceptAuth } = useAuth();
  const inviteQuery = useQuery({
    queryKey: ["invite-preview", code],
    queryFn: () => previewInvite(code),
    enabled: Boolean(code)
  });

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [sex, setSex] = useState("female");
  const [birthYear, setBirthYear] = useState("1995");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const payload = await registerByInvite({
        code,
        username,
        password,
        display_name: displayName,
        sex,
        birth_year: Number(birthYear)
      });
      acceptAuth(payload);
      navigate("/profile/setup", { replace: true });
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "加入失败。");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-card auth-card-featured">
        <div className="auth-hero">
          <p className="screen-eyebrow">邀请码加入</p>
          <h1>先加入家庭，再补齐你的资料</h1>
          <p className="screen-subtitle">邀请码：{code || "未提供"}</p>
        </div>
        <div className="auth-badge-row">
          <span className="auth-badge">成员创建</span>
          <span className="auth-badge">年龄 / 性别</span>
          <span className="auth-badge">报表同步</span>
        </div>
        {inviteQuery.data ? <p className="status-banner status-info">当前邀请码角色：{inviteQuery.data.role}</p> : null}
        {inviteQuery.isError ? (
          <p className="status-banner status-error">
            {inviteQuery.error instanceof Error ? inviteQuery.error.message : "邀请码不可用。"}
          </p>
        ) : null}
        <form className="stack-form auth-form-shell" onSubmit={handleSubmit}>
          <label className="field">
            <span>用户名</span>
            <input value={username} onChange={(event) => setUsername(event.target.value)} required />
          </label>
          <label className="field">
            <span>显示名</span>
            <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} required />
          </label>
          <label className="field">
            <span>密码</span>
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
          </label>
          <label className="field">
            <span>性别</span>
            <select value={sex} onChange={(event) => setSex(event.target.value)}>
              <option value="female">女</option>
              <option value="male">男</option>
            </select>
          </label>
          <label className="field">
            <span>出生年份（用于年龄 / TDEE）</span>
            <input type="number" min="1900" max="2100" value={birthYear} onChange={(event) => setBirthYear(event.target.value)} required />
          </label>
          {error ? <p className="status-banner status-error">{error}</p> : null}
          <button className="primary-button" type="submit" disabled={busy || inviteQuery.isError}>
            {busy ? "加入中…" : "加入并创建账号"}
          </button>
        </form>
        <p className="auth-footer">
          已有账号？
          <Link className="auth-inline-link" to="/login"> 返回登录</Link>
        </p>
      </section>
    </main>
  );
}

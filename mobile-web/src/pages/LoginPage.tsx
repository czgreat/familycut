import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../lib/auth";

export function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(username, password);
      navigate("/home", { replace: true });
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "登录失败。");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-card auth-card-featured">
        <div className="auth-hero">
          <p className="screen-eyebrow">FamilyCut Mobile</p>
          <h1>给 iPhone 用的家庭减脂入口</h1>
          <p className="screen-subtitle">登录后即可记录晨重、餐食并查看报表。</p>
        </div>

        <div className="auth-badge-row">
          <span className="auth-badge">PWA 主屏幕</span>
          <span className="auth-badge">餐食识别</span>
          <span className="auth-badge">日报长图</span>
        </div>

        <div className="auth-feature-grid">
          <article className="auth-feature">
            <strong>像 App 一样固定</strong>
            <span>支持主屏幕启动、沉浸式导航和轻离线草稿。</span>
          </article>
          <article className="auth-feature">
            <strong>餐食与报表在一处</strong>
            <span>记录进食、看热量差、导出和分享长图都走同一入口。</span>
          </article>
        </div>

        <form className="stack-form auth-form-shell" onSubmit={handleSubmit}>
          <label className="field">
            <span>用户名</span>
            <input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" required />
          </label>
          <label className="field">
            <span>密码</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          {error ? <p className="status-banner status-error">{error}</p> : null}
          <button className="primary-button" type="submit" disabled={busy}>
            {busy ? "登录中…" : "登录"}
          </button>
        </form>
        <p className="auth-footer">
          已有邀请链接的话，直接打开对应 `join` 地址即可。示例：
          <br />
          <Link className="auth-inline-link" to="/join/demo-code">/join/&lt;邀请码&gt;</Link>
        </p>
      </section>
    </main>
  );
}

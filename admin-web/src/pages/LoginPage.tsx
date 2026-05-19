import { FormEvent, useState } from "react";

type LoginPageProps = {
  busy: boolean;
  error: string;
  success: string;
  onLogin: (username: string, password: string) => Promise<void>;
};

export function LoginPage({ busy, error, success, onLogin }: LoginPageProps) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onLogin(username, password);
  }

  return (
    <main className="login-shell">
      <section className="login-card">
        <p className="eyebrow">FamilyCut</p>
        <h1>管理员登录</h1>
        <p className="login-copy">只有管理员可以登录后台。登录后才能查看成员数据、生成邀请码和维护设置。</p>

        <div className="hero-chip-row hero-chip-row-admin">
          <span className="hero-chip">成员后台</span>
          <span className="hero-chip">AI 配置</span>
          <span className="hero-chip">日报链路</span>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>管理员账号</span>
            <input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" />
          </label>
          <label className="field">
            <span>管理员密码</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              placeholder="请输入管理员密码"
            />
          </label>

          <button className="primary-button login-button" type="submit" disabled={busy}>
            {busy ? "登录中..." : "登录后台"}
          </button>
        </form>

        {success ? <p className="status-line status-success">{success}</p> : null}
        {error ? <p className="status-line status-error">{error}</p> : null}
        {!success && !error ? <p className="status-line">默认管理员账号：admin</p> : null}

        <div className="dashboard-mini-grid-admin">
          <article className="card dashboard-spotlight-card">
            <p className="eyebrow">登录后可做</p>
            <strong>成员 / 设置 / 报表</strong>
            <span>后台优先保证高密度和可操作性，不做展示页式跳转。</span>
          </article>
        </div>
      </section>
    </main>
  );
}

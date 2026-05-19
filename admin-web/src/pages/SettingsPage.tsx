import { FormEvent, useEffect, useMemo, useState } from "react";

import { AiConnectionTestResult, AppSettings, fetchAppSettings, saveAppSettings, testAiConnection } from "../lib/api";

type SettingsPageProps = {
  token: string;
};

const defaultSettings: AppSettings = {
  ai_enabled: true,
  ai_base_url: "http://localhost:23550/v1",
  ai_api_key: "sk-your-api-key",
  ai_model_name: "gemini-3-flash-preview",
  ai_timeout_sec: 60,
  ai_proxy_enabled: false,
  ai_proxy_url: "",
  report_generate_hour: 23,
  report_push_hour: 8,
  generic_webhook_enabled: false,
  generic_webhook_url: "",
  wechatbot_webhook_enabled: false,
  wechatbot_base_url: "",
  wechatbot_token: "",
  wechatbot_target: "",
  wechatbot_is_room: false
};

export function SettingsPage({ token }: SettingsPageProps) {
  const [settings, setSettings] = useState<AppSettings>(defaultSettings);
  const [status, setStatus] = useState("正在读取设置...");
  const [busy, setBusy] = useState(false);
  const [testBusy, setTestBusy] = useState(false);
  const [testResult, setTestResult] = useState<AiConnectionTestResult | null>(null);

  useEffect(() => {
    fetchAppSettings(token)
      .then((payload) => {
        setSettings(payload);
        setStatus("已从后端读取设置。");
      })
      .catch((error) => {
        setStatus(error instanceof Error ? error.message : "读取设置失败。");
      });
  }, [token]);

  const proxyUrlValue = useMemo(() => settings.ai_proxy_url ?? "", [settings.ai_proxy_url]);

  function updateSetting<Key extends keyof AppSettings>(key: Key, value: AppSettings[Key]) {
    setSettings((current) => ({ ...current, [key]: value }));
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      const payload = await saveAppSettings(token, {
        ...settings,
        ai_proxy_url: settings.ai_proxy_url?.trim() ? settings.ai_proxy_url : null,
        generic_webhook_url: settings.generic_webhook_url.trim(),
        wechatbot_base_url: settings.wechatbot_base_url.trim(),
        wechatbot_token: settings.wechatbot_token.trim(),
        wechatbot_target: settings.wechatbot_target.trim()
      });
      setSettings(payload);
      setStatus("设置已保存到后端。");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "保存失败。");
    } finally {
      setBusy(false);
    }
  }

  async function handleTestConnection() {
    setTestBusy(true);
    setTestResult(null);
    try {
      const result = await testAiConnection(token, {
        ai_base_url: settings.ai_base_url,
        ai_api_key: settings.ai_api_key,
        ai_model_name: settings.ai_model_name,
        ai_timeout_sec: settings.ai_timeout_sec,
        ai_proxy_enabled: settings.ai_proxy_enabled,
        ai_proxy_url: settings.ai_proxy_url
      });
      setTestResult(result);
      setStatus(result.ok ? "AI 测试连接成功。" : "AI 测试连接失败。");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "AI 测试连接失败。");
    } finally {
      setTestBusy(false);
    }
  }

  return (
    <div className="page">
      <section className="card dashboard-hero">
        <div className="dashboard-hero-copy">
          <p className="eyebrow">Settings</p>
          <h2>把 AI、通知和推送时间都固定在一个设置视图里</h2>
          <p className="dashboard-hero-note">后台优先保证可改、可读、可确认，不把关键配置藏在次级入口。</p>
        </div>
        <div className="hero-chip-row hero-chip-row-admin">
          <span className="hero-chip">AI {settings.ai_enabled ? "已启用" : "已关闭"}</span>
          <span className="hero-chip">生成 {settings.report_generate_hour}:00</span>
          <span className="hero-chip">推送 {settings.report_push_hour}:00</span>
        </div>
      </section>

      <section className="dashboard-mini-grid-admin">
        <article className="card dashboard-spotlight-card">
          <p className="eyebrow">当前模型</p>
          <strong>{settings.ai_model_name || "未配置"}</strong>
          <span>{settings.ai_base_url}</span>
        </article>
        <article className="card dashboard-spotlight-card">
          <p className="eyebrow">Proxy</p>
          <strong>{settings.ai_proxy_enabled ? "已启用" : "未启用"}</strong>
          <span>{settings.ai_proxy_url || "当前直连网关"}</span>
        </article>
        <article className="card dashboard-spotlight-card">
          <p className="eyebrow">Webhook</p>
          <strong>{settings.generic_webhook_enabled ? "已启用" : "未启用"}</strong>
          <span>{settings.generic_webhook_url || "当前未配置地址"}</span>
        </article>
      </section>

      <section className="section">
        <div className="section-header">
          <div>
            <p className="eyebrow">设置</p>
            <h2>AI、proxy、日报时间和通知配置</h2>
          </div>
        </div>

        <form className="card settings-form" onSubmit={handleSave}>
          <section className="settings-cluster">
            <div className="settings-cluster-header">
              <div>
                <p className="eyebrow">AI Core</p>
                <h3>视觉模型与网关</h3>
              </div>
            </div>
            <div className="form-grid">
              <label className="field">
                <span>AI Base URL</span>
                <input
                  value={settings.ai_base_url}
                  onChange={(event) => updateSetting("ai_base_url", event.target.value)}
                  placeholder="http://localhost:23550/v1"
                />
              </label>
              <label className="field">
                <span>AI 模型名</span>
                <input
                  value={settings.ai_model_name}
                  onChange={(event) => updateSetting("ai_model_name", event.target.value)}
                  placeholder="gemini-3-flash-preview"
                />
              </label>
              <label className="field field-full">
                <span>API Key</span>
                <input
                  type="password"
                  value={settings.ai_api_key}
                  onChange={(event) => updateSetting("ai_api_key", event.target.value)}
                  placeholder="sk-..."
                />
              </label>
              <label className="field">
                <span>超时时间（秒）</span>
                <input
                  type="number"
                  min={5}
                  max={300}
                  value={settings.ai_timeout_sec}
                  onChange={(event) => updateSetting("ai_timeout_sec", Number(event.target.value))}
                />
              </label>
            </div>
            <div className="actions actions-inline">
              <button className="secondary-button" type="button" onClick={() => void handleTestConnection()} disabled={testBusy}>
                {testBusy ? "测试中..." : "测试连接"}
              </button>
            </div>
            {testResult ? (
              <div className={testResult.ok ? "status-line status-success page-banner" : "status-line status-error page-banner"}>
                <strong>{testResult.ok ? "连接成功" : "连接失败"}</strong>
                <div>模式：{testResult.transport}</div>
                <div>模型：{testResult.model_name}</div>
                <div>{testResult.detail}</div>
              </div>
            ) : null}
          </section>

          <section className="settings-cluster">
            <div className="settings-cluster-header">
              <div>
                <p className="eyebrow">Schedule</p>
                <h3>日报生成与推送</h3>
              </div>
            </div>
            <div className="form-grid">
              <label className="field">
                <span>日报生成小时</span>
                <input
                  type="number"
                  min={0}
                  max={23}
                  value={settings.report_generate_hour}
                  onChange={(event) => updateSetting("report_generate_hour", Number(event.target.value))}
                />
              </label>
              <label className="field">
                <span>日报推送小时</span>
                <input
                  type="number"
                  min={0}
                  max={23}
                  value={settings.report_push_hour}
                  onChange={(event) => updateSetting("report_push_hour", Number(event.target.value))}
                />
              </label>
              <label className="field field-full">
                <span>generic webhook 地址</span>
                <input
                  value={settings.generic_webhook_url}
                  onChange={(event) => updateSetting("generic_webhook_url", event.target.value)}
                  placeholder="https://example.com/webhook"
                />
              </label>
            </div>
          </section>

          <section className="settings-cluster">
            <div className="settings-cluster-header">
              <div>
                <p className="eyebrow">Switches</p>
                <h3>启用状态</h3>
              </div>
            </div>
            <div className="toggle-grid">
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={settings.ai_enabled}
                  onChange={(event) => updateSetting("ai_enabled", event.target.checked)}
                />
                <span>启用 AI</span>
              </label>
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={settings.ai_proxy_enabled}
                  onChange={(event) => updateSetting("ai_proxy_enabled", event.target.checked)}
                />
                <span>启用 proxy</span>
              </label>
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={settings.generic_webhook_enabled}
                  onChange={(event) => updateSetting("generic_webhook_enabled", event.target.checked)}
                />
                <span>启用 generic webhook</span>
              </label>
            </div>
          </section>

          <section className="settings-cluster">
            <div className="settings-cluster-header">
              <div>
                <p className="eyebrow">Wechatbot</p>
                <h3>群聊推送</h3>
              </div>
            </div>
            <label className="field field-full">
              <span>proxy 地址</span>
              <input
                value={proxyUrlValue}
                onChange={(event) => updateSetting("ai_proxy_url", event.target.value)}
                placeholder="http://127.0.0.1:7890"
                disabled={!settings.ai_proxy_enabled}
              />
            </label>

            <div className="form-grid">
              <label className="field">
                <span>wechatbot Base URL</span>
                <input
                  value={settings.wechatbot_base_url}
                  onChange={(event) => updateSetting("wechatbot_base_url", event.target.value)}
                  placeholder="http://localhost:3001"
                />
              </label>
              <label className="field">
                <span>wechatbot Token</span>
                <input
                  value={settings.wechatbot_token}
                  onChange={(event) => updateSetting("wechatbot_token", event.target.value)}
                  placeholder="token"
                />
              </label>
              <label className="field">
                <span>发送对象</span>
                <input
                  value={settings.wechatbot_target}
                  onChange={(event) => updateSetting("wechatbot_target", event.target.value)}
                  placeholder="wxid 或群名"
                />
              </label>
            </div>

            <div className="toggle-grid">
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={settings.wechatbot_webhook_enabled}
                  onChange={(event) => updateSetting("wechatbot_webhook_enabled", event.target.checked)}
                />
                <span>启用 wechatbot-webhook</span>
              </label>
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={settings.wechatbot_is_room}
                  onChange={(event) => updateSetting("wechatbot_is_room", event.target.checked)}
                />
                <span>发送到群聊</span>
              </label>
            </div>
          </section>

          <p className="status-line">{status}</p>
          <div className="actions">
            <button className="primary-button" type="submit" disabled={busy}>
              {busy ? "保存中..." : "保存设置"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

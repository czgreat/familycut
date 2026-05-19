import { useEffect, useState } from "react";

import { Section } from "../components/Section";
import { StatCard } from "../components/StatCard";
import {
  DailyReportSummary,
  DashboardSummary,
  fetchDashboard,
  fetchHouseholdSelfies,
  fetchRecentHouseholdReports,
  MediaAsset
} from "../lib/api";

const defaultSummary: DashboardSummary = {
  member_count: 0,
  measurement_count: 0,
  meal_count: 0,
  shared_media_count: 0
};

type DashboardPageProps = {
  token: string;
};

export function DashboardPage({ token }: DashboardPageProps) {
  const [summary, setSummary] = useState<DashboardSummary>(defaultSummary);
  const [reports, setReports] = useState<DailyReportSummary[]>([]);
  const [selfies, setSelfies] = useState<MediaAsset[]>([]);

  useEffect(() => {
    fetchDashboard(token).then(setSummary).catch(() => setSummary(defaultSummary));
    fetchRecentHouseholdReports(token).then((payload) => setReports(payload.slice(0, 8))).catch(() => setReports([]));
    fetchHouseholdSelfies(token).then((payload) => setSelfies(payload.slice(0, 8))).catch(() => setSelfies([]));
  }, [token]);

  return (
    <div className="page">
      <section className="card dashboard-hero">
        <div className="dashboard-hero-copy">
          <p className="eyebrow">Overview</p>
          <h2>把成员、日报和媒体流放进一个桌面化控制台</h2>
          <p className="dashboard-hero-note">后台优先保证数据密度和配置可控，同时统一成更接近 macOS 26 的玻璃工作区。</p>
        </div>
        <div className="hero-chip-row hero-chip-row-admin">
          <span className="hero-chip">成员 {summary.member_count}</span>
          <span className="hero-chip">餐食 {summary.meal_count}</span>
          <span className="hero-chip">日报 {reports.length}</span>
        </div>
      </section>

      <Section title="概览" description="家庭数据总览">
        <div className="stats-grid">
          <StatCard label="成员数" value={String(summary.member_count)} hint="当前家庭中已加入的成员数量" />
          <StatCard label="体重记录" value={String(summary.measurement_count)} hint="累计晨重与体征记录" />
          <StatCard label="餐食记录" value={String(summary.meal_count)} hint="手动记餐和 AI 识别入库的总数" />
          <StatCard label="自拍数量" value={String(summary.shared_media_count)} hint="当前后台可见的共享自拍数量" />
        </div>
      </Section>

      <section className="dashboard-mini-grid-admin">
        <article className="card dashboard-spotlight-card">
          <p className="eyebrow">最近日报</p>
          <strong>{reports[0]?.report_date ?? "暂无"}</strong>
          <span>{reports[0] ? `状态 ${reports[0].status}` : "等待成员产生日报数据"}</span>
        </article>
        <article className="card dashboard-spotlight-card">
          <p className="eyebrow">最近自拍</p>
          <strong>{selfies[0] ? new Date(selfies[0].captured_at).toLocaleDateString("zh-CN") : "暂无"}</strong>
          <span>{selfies[0]?.note || "等待新的共享自拍进入后台"}</span>
        </article>
        <article className="card dashboard-spotlight-card">
          <p className="eyebrow">当前链路</p>
          <strong>数据 / 报表 / AI</strong>
          <span>后台继续保持高密可读，避免变成展示页。</span>
        </article>
      </section>

      <Section title="最近日报" description="后台可直接查看近几天的生成结果">
        <div className="card-list">
          {reports.length > 0 ? (
            reports.map((report) => (
              <article key={report.id} className="card report-card-admin">
                <h3>{report.report_date}</h3>
                {report.image_url ? <img className="report-preview" src={report.image_url} alt="日报长图预览" /> : null}
                <div className="report-meta-row">
                  <span>状态：{report.status}</span>
                  <span>热量差：{renderNumber(report.payload.deficit_kcal)} kcal</span>
                </div>
                <div className="report-meta-row">
                  <span>碳水：{renderNumber((report.payload.intake as Record<string, unknown> | undefined)?.carb_g)} g</span>
                  <span>脂肪：{renderNumber((report.payload.intake as Record<string, unknown> | undefined)?.fat_g)} g</span>
                  <span>蛋白质：{renderNumber((report.payload.intake as Record<string, unknown> | undefined)?.protein_g)} g</span>
                </div>
                <p>是否达标：{report.payload.deficit_hit ? "达标" : "未达标"}</p>
              </article>
            ))
          ) : (
            <article className="card">
              <h3>还没有日报数据</h3>
              <p>等成员录入体重和餐食后，日报会在后台自动生成。</p>
            </article>
          )}
        </div>
      </Section>

      <Section title="最近共享自拍" description="当前后台可见的共享自拍会显示在这里">
        {selfies.length > 0 ? (
          <div className="photo-grid">
            {selfies.map((asset) => (
              <article key={asset.id} className="photo-card">
                {asset.preview_url ? <img src={asset.preview_url} alt="家庭自拍" /> : null}
                <div className="photo-meta">
                  <strong>{new Date(asset.captured_at).toLocaleString("zh-CN")}</strong>
                  <span>{asset.note || "无备注"}</span>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="card photo-empty">
            <h3>还没有自拍记录</h3>
            <p>App 上传自拍后，这里会自动出现时间流。</p>
          </div>
        )}
      </Section>
    </div>
  );
}

function renderNumber(value: unknown): string {
  return typeof value === "number" ? String(Math.round(value)) : "暂无";
}

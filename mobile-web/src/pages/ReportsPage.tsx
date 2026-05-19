import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { Screen } from "../components/Screen";
import { fetchDailyReport, fetchMonthlyReport, fetchRecentReports, fetchWeeklyReport } from "../lib/api";
import { useAuth } from "../lib/auth";
import { downloadUrl, shareImageFile } from "../lib/share";
import { formatDateLabel, getCurrentMonth, getTodayDate, getWeekStart } from "../lib/utils";

function numberValue(value: unknown): number | null {
  return typeof value === "number" ? value : null;
}

export function ReportsPage() {
  const { session } = useAuth();
  const today = getTodayDate();
  const weekStart = getWeekStart();
  const currentMonth = getCurrentMonth();
  const reportsQuery = useQuery({
    queryKey: ["reports", "recent"],
    queryFn: () => fetchRecentReports(session!.accessToken),
    enabled: Boolean(session?.accessToken)
  });
  const dailyQuery = useQuery({
    queryKey: ["report-card", "daily", today],
    queryFn: () => fetchDailyReport(session!.accessToken, today),
    enabled: Boolean(session?.accessToken)
  });
  const weeklyQuery = useQuery({
    queryKey: ["report-card", "weekly", weekStart],
    queryFn: () => fetchWeeklyReport(session!.accessToken, weekStart),
    enabled: Boolean(session?.accessToken)
  });
  const monthlyQuery = useQuery({
    queryKey: ["report-card", "monthly", currentMonth],
    queryFn: () => fetchMonthlyReport(session!.accessToken, currentMonth),
    enabled: Boolean(session?.accessToken)
  });

  async function handleExport(url: string | null | undefined, fileName: string) {
    if (!url) {
      return;
    }
    await downloadUrl(url, fileName);
  }

  async function handleShare(input: { title: string; text: string; url: string | null | undefined }) {
    if (!input.url) {
      return;
    }
    const suffix = input.title.includes("日报")
      ? today
      : input.title.includes("周报")
        ? weekStart
        : currentMonth;
    const kind = input.title.includes("日报") ? "daily" : input.title.includes("周报") ? "weekly" : "monthly";
    await shareImageFile({
      title: input.title,
      text: input.text,
      url: input.url,
      fileName: `familycut-${kind}-${suffix}.png`
    });
  }

  const dailyDeficit = numberValue(dailyQuery.data?.payload?.deficit_kcal);
  const weeklyHitDays = numberValue(weeklyQuery.data?.payload?.hit_days);
  const weeklyTotalDays = numberValue(weeklyQuery.data?.payload?.total_days);
  const monthlyAvgIntake = numberValue(monthlyQuery.data?.payload?.avg_intake_kcal);
  const dailyIntake = typeof dailyQuery.data?.payload?.intake === "object" && dailyQuery.data?.payload?.intake ? (dailyQuery.data.payload.intake as Record<string, unknown>) : null;
  const weeklyAvgIntake = typeof weeklyQuery.data?.payload?.avg_intake === "object" && weeklyQuery.data?.payload?.avg_intake ? (weeklyQuery.data.payload.avg_intake as Record<string, unknown>) : null;
  const monthlyAvgIntakeMap = typeof monthlyQuery.data?.payload?.avg_intake === "object" && monthlyQuery.data?.payload?.avg_intake ? (monthlyQuery.data.payload.avg_intake as Record<string, unknown>) : null;

  return (
    <Screen title="报表" subtitle="查看日报、周报、月报，并支持导出或分享图片。">
      <section className="panel panel-hero">
        <div className="hero-panel-grid">
          <div className="hero-panel-primary">
            <p className="screen-eyebrow">Report Deck</p>
            <h2>把日报、周报、月报都收进同一处</h2>
            <p className="panel-muted">先看今日状态，再回看本周和本月趋势。分享和导出保持图片优先。</p>
          </div>
          <div className="hero-chip-row">
            <span className="hero-chip">日报 {dailyQuery.data?.status ?? "待拉取"}</span>
            <span className="hero-chip">周报 {weeklyQuery.data?.status ?? "待拉取"}</span>
            <span className="hero-chip">月报 {monthlyQuery.data?.status ?? "待拉取"}</span>
          </div>
        </div>
      </section>

      <section className="dashboard-mini-grid">
        <section className="panel">
          <div className="panel-header">
            <h2>今日摘要</h2>
            <span>日报</span>
          </div>
          <div className="mini-feed">
            <article className="mini-feed-item">
              <strong>{dailyQuery.data?.status ?? "待生成"}</strong>
              <span>
                {dailyDeficit !== null ? `热量差 ${Math.round(dailyDeficit)} kcal` : "等待今日长图和摘要生成"}
                {dailyIntake && typeof dailyIntake.carb_g === "number"
                  ? ` · 碳水 ${Number(dailyIntake.carb_g).toFixed(1)}g / 脂肪 ${Number(dailyIntake.fat_g ?? 0).toFixed(1)}g / 蛋白质 ${Number(dailyIntake.protein_g ?? 0).toFixed(1)}g`
                  : ""}
              </span>
            </article>
          </div>
        </section>
        <section className="panel">
          <div className="panel-header">
            <h2>本周摘要</h2>
            <span>周报</span>
          </div>
          <div className="mini-feed">
            <article className="mini-feed-item">
              <strong>{weeklyQuery.data?.status ?? "待生成"}</strong>
              <span>
                {weeklyHitDays !== null && weeklyTotalDays !== null
                  ? `达标 ${Math.round(weeklyHitDays)} / ${Math.round(weeklyTotalDays)} 天`
                  : "等待本周小结生成"}
                {weeklyAvgIntake && typeof weeklyAvgIntake.carb_g === "number"
                  ? ` · 碳水 ${Number(weeklyAvgIntake.carb_g).toFixed(1)}g / 脂肪 ${Number(weeklyAvgIntake.fat_g ?? 0).toFixed(1)}g / 蛋白质 ${Number(weeklyAvgIntake.protein_g ?? 0).toFixed(1)}g`
                  : ""}
              </span>
            </article>
          </div>
        </section>
        <section className="panel">
          <div className="panel-header">
            <h2>本月摘要</h2>
            <span>月报</span>
          </div>
          <div className="mini-feed">
            <article className="mini-feed-item">
              <strong>{monthlyQuery.data?.status ?? "待生成"}</strong>
              <span>
                {monthlyAvgIntake !== null ? `平均摄入 ${Math.round(monthlyAvgIntake)} kcal / 天` : "等待本月小结生成"}
                {monthlyAvgIntakeMap && typeof monthlyAvgIntakeMap.carb_g === "number"
                  ? ` · 碳水 ${Number(monthlyAvgIntakeMap.carb_g).toFixed(1)}g / 脂肪 ${Number(monthlyAvgIntakeMap.fat_g ?? 0).toFixed(1)}g / 蛋白质 ${Number(monthlyAvgIntakeMap.protein_g ?? 0).toFixed(1)}g`
                  : ""}
              </span>
            </article>
          </div>
        </section>
      </section>

      <div className="report-card-grid">
        <article className="action-card report-card">
          <span>日报</span>
          <strong>{formatDateLabel(today)}</strong>
          <p className="report-card-hint">{dailyQuery.data?.status ?? "正在生成或拉取今日长图"}</p>
          <div className="report-card-actions">
            <button className="secondary-button" type="button" onClick={() => void handleExport(dailyQuery.data?.image_url, `familycut-daily-${today}.png`)}>
              导出
            </button>
            <button
              className="secondary-button secondary-button-muted"
              type="button"
              onClick={() => void handleShare({ title: `日报 · ${today}`, text: "分享今日日报", url: dailyQuery.data?.image_url })}
            >
              分享
            </button>
            <Link className="report-card-link" to={`/reports/daily/${today}`}>
              详情
            </Link>
          </div>
        </article>
        <article className="action-card report-card">
          <span>周报</span>
          <strong>起始于 {weekStart}</strong>
          <p className="report-card-hint">{weeklyQuery.data?.status ?? "正在生成或拉取本周长图"}</p>
          <div className="report-card-actions">
            <button className="secondary-button" type="button" onClick={() => void handleExport(weeklyQuery.data?.image_url, `familycut-weekly-${weekStart}.png`)}>
              导出
            </button>
            <button
              className="secondary-button secondary-button-muted"
              type="button"
              onClick={() => void handleShare({ title: `周报 · ${weekStart}`, text: "分享本周周报", url: weeklyQuery.data?.image_url })}
            >
              分享
            </button>
            <Link className="report-card-link" to={`/reports/weekly/${weekStart}`}>
              详情
            </Link>
          </div>
        </article>
        <article className="action-card report-card">
          <span>月报</span>
          <strong>{currentMonth}</strong>
          <p className="report-card-hint">{monthlyQuery.data?.status ?? "正在生成或拉取本月长图"}</p>
          <div className="report-card-actions">
            <button className="secondary-button" type="button" onClick={() => void handleExport(monthlyQuery.data?.image_url, `familycut-monthly-${currentMonth}.png`)}>
              导出
            </button>
            <button
              className="secondary-button secondary-button-muted"
              type="button"
              onClick={() => void handleShare({ title: `月报 · ${currentMonth}`, text: "分享本月月报", url: monthlyQuery.data?.image_url })}
            >
              分享
            </button>
            <Link className="report-card-link" to={`/reports/monthly/${currentMonth}`}>
              详情
            </Link>
          </div>
        </article>
      </div>

      <section className="panel">
        <div className="panel-header">
          <h2>最近日报</h2>
          <span>{reportsQuery.data?.length ?? 0} 条</span>
        </div>
        <div className="timeline">
          {(reportsQuery.data ?? []).map((report) => (
            <Link key={report.id} className="timeline-item timeline-item-link" to={`/reports/daily/${report.report_date}`}>
              <strong>{report.report_date}</strong>
              <span>
                {report.status} ·
                {typeof report.payload.deficit_kcal === "number" ? ` 热量差 ${report.payload.deficit_kcal as number} kcal` : " 查看长图"}
              </span>
            </Link>
          ))}
        </div>
      </section>
    </Screen>
  );
}

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { Screen } from "../components/Screen";
import { StatCard } from "../components/StatCard";
import { fetchRecentReports, listMeals, listMeasurements } from "../lib/api";
import { useAuth } from "../lib/auth";
import { loadHomeSnapshot, saveHomeSnapshot } from "../lib/offline";
import { formatDateLabel, formatNumber, getTodayDate } from "../lib/utils";

type CachedHome = {
  latestWeightKg: number | null;
  latestBodyFatPct: number | null;
  mealsToday: number;
  totalKcalToday: number;
  latestReportDate: string | null;
  latestDeficitKcal: number | null;
};

export function HomePage() {
  const { session, member } = useAuth();
  const [cached, setCached] = useState<CachedHome | null>(null);
  const today = getTodayDate();

  const measurementsQuery = useQuery({
    queryKey: ["measurements"],
    queryFn: () => listMeasurements(session!.accessToken),
    enabled: Boolean(session?.accessToken)
  });

  const mealsQuery = useQuery({
    queryKey: ["meals", today],
    queryFn: () => listMeals(session!.accessToken, today),
    enabled: Boolean(session?.accessToken)
  });

  const reportsQuery = useQuery({
    queryKey: ["reports", "recent"],
    queryFn: () => fetchRecentReports(session!.accessToken, 3),
    enabled: Boolean(session?.accessToken)
  });

  useEffect(() => {
    void loadHomeSnapshot().then((snapshot) => {
      if (snapshot) {
        setCached(snapshot);
      }
    });
  }, []);

  useEffect(() => {
    if (!measurementsQuery.data || !mealsQuery.data || !reportsQuery.data) {
      return;
    }
    const latestMeasurement = measurementsQuery.data[0];
    const latestReport = reportsQuery.data[0];
    const totalKcalToday = mealsQuery.data.reduce((sum, meal) => sum + meal.kcal, 0);
    const nextSnapshot: CachedHome = {
      latestWeightKg: latestMeasurement?.weight_kg ?? null,
      latestBodyFatPct: latestMeasurement?.body_fat_pct ?? null,
      mealsToday: mealsQuery.data.length,
      totalKcalToday,
      latestReportDate: latestReport?.report_date ?? null,
      latestDeficitKcal:
        typeof latestReport?.payload.deficit_kcal === "number" ? (latestReport.payload.deficit_kcal as number) : null
    };
    setCached(nextSnapshot);
    void saveHomeSnapshot(nextSnapshot);
  }, [mealsQuery.data, measurementsQuery.data, reportsQuery.data]);

  const latestMeasurement = measurementsQuery.data?.[0];
  const latestReport = reportsQuery.data?.[0];
  const mealsToday = mealsQuery.data?.length ?? cached?.mealsToday ?? 0;
  const totalKcalToday = mealsQuery.data?.reduce((sum, meal) => sum + meal.kcal, 0) ?? cached?.totalKcalToday ?? 0;
  const latestDeficit =
    typeof latestReport?.payload.deficit_kcal === "number"
      ? (latestReport.payload.deficit_kcal as number)
      : cached?.latestDeficitKcal;
  const latestMacros =
    latestReport && typeof latestReport.payload === "object" && latestReport.payload.intake && typeof latestReport.payload.intake === "object"
      ? (latestReport.payload.intake as { carb_g?: number; fat_g?: number; protein_g?: number })
      : null;

  return (
    <Screen
      title={`你好，${member?.display_name ?? "成员"}`}
      subtitle={`${formatDateLabel(today)}。查看今天的体重、餐食和报表摘要。`}
      eyebrow="Today"
    >
      <section className="panel panel-hero">
        <div className="hero-panel-grid">
          <div className="hero-panel-primary">
            <p className="screen-eyebrow">Daily Orbit</p>
            <h2>今天先看体重、摄入和热量差</h2>
            <p className="panel-muted">保持输入顺序稳定：晨重、餐食、报表，能让日报和 TDEE 更可信。</p>
          </div>
          <div className="hero-chip-row">
            <span className="hero-chip">今日餐次 {mealsToday}</span>
            <span className="hero-chip">摄入 {formatNumber(totalKcalToday, 0)} kcal</span>
            <span className="hero-chip">最近缺口 {formatNumber(latestDeficit, 0)} kcal</span>
          </div>
        </div>
      </section>

      <div className="grid-cards">
        <StatCard label="最近体重" value={`${formatNumber(latestMeasurement?.weight_kg ?? cached?.latestWeightKg)} kg`} />
        <StatCard label="最近体脂" value={`${formatNumber(latestMeasurement?.body_fat_pct ?? cached?.latestBodyFatPct)} %`} tone="light" />
        <StatCard label="今日餐次" value={String(mealsToday)} hint={`总热量 ${formatNumber(totalKcalToday, 0)} kcal`} />
        <StatCard
          label="最近热量差"
          value={`${formatNumber(
            typeof latestReport?.payload.deficit_kcal === "number"
              ? (latestReport.payload.deficit_kcal as number)
              : cached?.latestDeficitKcal,
            0
          )} kcal`}
          hint={latestReport?.report_date ?? cached?.latestReportDate ?? "暂无日报"}
          tone="light"
        />
      </div>

      <section className="panel">
        <div className="panel-header">
          <h2>宏量营养</h2>
          <span>最近日报</span>
        </div>
        <div className="summary-grid">
          <article className="summary-item">
            <strong>碳水</strong>
            <span>{latestMacros?.carb_g !== undefined ? `${latestMacros.carb_g.toFixed(1)} g` : "--"}</span>
          </article>
          <article className="summary-item">
            <strong>脂肪</strong>
            <span>{latestMacros?.fat_g !== undefined ? `${latestMacros.fat_g.toFixed(1)} g` : "--"}</span>
          </article>
          <article className="summary-item">
            <strong>蛋白质</strong>
            <span>{latestMacros?.protein_g !== undefined ? `${latestMacros.protein_g.toFixed(1)} g` : "--"}</span>
          </article>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>今日捷径</h2>
          <span>高频入口</span>
        </div>
        <div className="quick-action-grid">
          <Link className="action-card quick-action-card" to="/weight">
            <span>晨重</span>
            <strong>记录今天的体重和体脂</strong>
          </Link>
          <Link className="action-card quick-action-card" to="/meals">
            <span>餐食</span>
            <strong>手动记餐或直接拍照识别</strong>
          </Link>
          <Link className="action-card quick-action-card" to={`/reports/daily/${today}`}>
            <span>日报</span>
            <strong>查看今天的长图与摘要</strong>
          </Link>
        </div>
      </section>

      <section className="dashboard-mini-grid">
        <section className="panel">
          <div className="panel-header">
            <h2>最近体重</h2>
            <span>{measurementsQuery.data?.length ?? 0} 条</span>
          </div>
          <div className="mini-feed">
            {(measurementsQuery.data ?? []).slice(0, 3).map((item) => (
              <article className="mini-feed-item" key={item.id}>
                <strong>{item.weight_kg.toFixed(1)} kg</strong>
                <span>
                  {item.body_fat_pct ? `${item.body_fat_pct.toFixed(1)}%` : "未填体脂"} · {new Date(item.measured_at).toLocaleDateString("zh-CN")}
                </span>
              </article>
            ))}
            {(measurementsQuery.data ?? []).length === 0 ? <p className="panel-muted">还没有晨重记录。</p> : null}
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <h2>最近餐食</h2>
            <span>{mealsQuery.data?.length ?? 0} 条</span>
          </div>
          <div className="mini-feed">
            {(mealsQuery.data ?? []).slice(0, 3).map((meal) => (
              <article className="mini-feed-item" key={meal.id}>
                <strong>{meal.food_name}</strong>
                <span>{meal.actual_grams.toFixed(0)} g · {meal.kcal.toFixed(0)} kcal</span>
              </article>
            ))}
            {(mealsQuery.data ?? []).length === 0 ? <p className="panel-muted">今天还没有餐食记录。</p> : null}
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <h2>最近日报</h2>
            <span>{reportsQuery.data?.length ?? 0} 条</span>
          </div>
          <div className="mini-feed">
            {(reportsQuery.data ?? []).slice(0, 3).map((report) => (
              <article className="mini-feed-item" key={report.id}>
                <strong>{report.report_date}</strong>
                <span>
                  {report.status}
                  {typeof report.payload.deficit_kcal === "number" ? ` · 热量差 ${Math.round(report.payload.deficit_kcal as number)} kcal` : ""}
                </span>
              </article>
            ))}
            {(reportsQuery.data ?? []).length === 0 ? <p className="panel-muted">还没有日报记录。</p> : null}
          </div>
        </section>
      </section>
    </Screen>
  );
}

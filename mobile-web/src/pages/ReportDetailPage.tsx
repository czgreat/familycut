import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { Screen } from "../components/Screen";
import { DailyReport, PeriodicReport, fetchDailyReport, fetchMonthlyReport, fetchWeeklyReport } from "../lib/api";
import { useAuth } from "../lib/auth";
import { downloadUrl, shareImageFile } from "../lib/share";
import { formatDateLabel, resolveAssetUrl } from "../lib/utils";

type Props = {
  kind: "daily" | "weekly" | "monthly";
};

type NormalizedReport = {
  title: string;
  subtitle: string;
  imageUrl: string | null;
  payload: Record<string, unknown>;
};

type SummaryItem = {
  label: string;
  value: string;
};

function readNumber(value: unknown): number | null {
  return typeof value === "number" ? value : typeof value === "string" ? Number(value) : null;
}

function readNestedNumber(payload: Record<string, unknown>, primaryKey: string, nestedKey: string): number | null {
  const container = payload[primaryKey];
  if (!container || typeof container !== "object") {
    return null;
  }
  return readNumber((container as Record<string, unknown>)[nestedKey]);
}

function formatMetric(value: number | null, suffix: string, digits = 0): string {
  if (value === null || Number.isNaN(value)) {
    return "--";
  }
  return suffix === "%" ? `${value.toFixed(digits)}${suffix}` : `${value.toFixed(digits)} ${suffix}`;
}

function buildSummaryItems(kind: Props["kind"], payload: Record<string, unknown>): SummaryItem[] {
  if (kind === "daily") {
    const carbG = readNestedNumber(payload, "intake", "carb_g");
    const proteinG = readNestedNumber(payload, "intake", "protein_g");
    const fatG = readNestedNumber(payload, "intake", "fat_g");
    const carbPct = readNestedNumber(payload, "macro_ratio", "carb_pct");
    const proteinPct = readNestedNumber(payload, "macro_ratio", "protein_pct");
    const fatPct = readNestedNumber(payload, "macro_ratio", "fat_pct");
    const carbTarget = readNestedNumber(payload, "macro_target", "carb_g");
    const proteinTarget = readNestedNumber(payload, "macro_target", "protein_g");
    const fatTarget = readNestedNumber(payload, "macro_target", "fat_g");
    const macroStatus = (payload["macro_status"] ?? null) as Record<string, { status?: string }> | null;
    const statusLabel = (value: string | undefined) =>
      value === "on_target" ? "达标" : value === "low" ? "偏低" : value === "high" ? "偏高" : "待计算";
    return [
      { label: "最新体重", value: formatMetric(readNumber(payload["weight_kg"]), "kg", 1) },
      { label: "基础代谢 BMR", value: formatMetric(readNumber(payload["bmr"]), "kcal") },
      { label: "今日 TDEE", value: formatMetric(readNumber(payload["tdee"]), "kcal") },
      { label: "目标摄入", value: formatMetric(readNumber(payload["goal_intake_kcal"]), "kcal") },
      { label: "今日摄入", value: formatMetric(readNestedNumber(payload, "intake", "kcal"), "kcal") },
      { label: "热量差", value: formatMetric(readNumber(payload["deficit_kcal"]), "kcal") },
      { label: "碳水", value: carbG !== null ? `${carbG.toFixed(1)} g · ${formatMetric(carbPct, "%")}` : "--" },
      { label: "碳水目标", value: carbTarget !== null ? `${carbTarget.toFixed(1)} g · ${statusLabel(macroStatus?.carb?.status)}` : "--" },
      { label: "蛋白质", value: proteinG !== null ? `${proteinG.toFixed(1)} g · ${formatMetric(proteinPct, "%")}` : "--" },
      { label: "蛋白目标", value: proteinTarget !== null ? `${proteinTarget.toFixed(1)} g · ${statusLabel(macroStatus?.protein?.status)}` : "--" },
      { label: "脂肪", value: fatG !== null ? `${fatG.toFixed(1)} g · ${formatMetric(fatPct, "%")}` : "--" },
      { label: "脂肪目标", value: fatTarget !== null ? `${fatTarget.toFixed(1)} g · ${statusLabel(macroStatus?.fat?.status)}` : "--" }
    ];
  }

  const avgIntake = (payload["avg_intake"] ?? null) as Record<string, unknown> | null;
  const avgIntakeKcal = avgIntake ? readNumber(avgIntake["kcal"]) : readNumber(payload["avg_intake_kcal"]);
  const avgCarb = avgIntake ? readNumber(avgIntake["carb_g"]) : null;
  const avgProtein = avgIntake ? readNumber(avgIntake["protein_g"]) : null;
  const avgFat = avgIntake ? readNumber(avgIntake["fat_g"]) : null;
  return [
    { label: "平均摄入", value: formatMetric(avgIntakeKcal, "kcal / 天") },
    { label: "平均热量差", value: formatMetric(readNumber(payload["avg_deficit_kcal"]), "kcal / 天") },
    { label: "达标天数", value: `${formatMetric(readNumber(payload["hit_days"]), "天")} / ${formatMetric(readNumber(payload["total_days"]), "天")}` },
    { label: "体重变化", value: formatMetric(readNumber(payload["weight_change_kg"]), "kg", 1) },
    { label: "平均碳水", value: formatMetric(avgCarb, "g / 天", 1) },
    { label: "平均蛋白质", value: formatMetric(avgProtein, "g / 天", 1) },
    { label: "平均脂肪", value: formatMetric(avgFat, "g / 天", 1) }
  ];
}

function normalizeReport(kind: Props["kind"], report: DailyReport | PeriodicReport): NormalizedReport {
  if (kind === "daily") {
    const daily = report as DailyReport;
    return {
      title: `日报 · ${daily.report_date}`,
      subtitle: formatDateLabel(daily.report_date),
      imageUrl: resolveAssetUrl(daily.image_url ?? null),
      payload: daily.payload
    };
  }
  const periodic = report as PeriodicReport;
  return {
    title: `${kind === "weekly" ? "周报" : "月报"} · ${periodic.period_start}`,
    subtitle: `${periodic.period_start} 至 ${periodic.period_end}`,
    imageUrl: resolveAssetUrl(periodic.image_url ?? null),
    payload: periodic.payload
  };
}

export function ReportDetailPage({ kind }: Props) {
  const { session } = useAuth();
  const params = useParams();
  const [notice, setNotice] = useState("");
  const targetValue = kind === "daily" ? params.date : kind === "weekly" ? params.startDate : params.yearMonth;

  const reportQuery = useQuery({
    queryKey: ["report", kind, targetValue],
    queryFn: async () => {
      if (!session?.accessToken || !targetValue) {
        throw new Error("缺少报表参数。");
      }
      if (kind === "daily") {
        return fetchDailyReport(session.accessToken, targetValue);
      }
      if (kind === "weekly") {
        return fetchWeeklyReport(session.accessToken, targetValue);
      }
      return fetchMonthlyReport(session.accessToken, targetValue);
    },
    enabled: Boolean(session?.accessToken && targetValue)
  });

  const normalized = useMemo(() => (reportQuery.data ? normalizeReport(kind, reportQuery.data) : null), [kind, reportQuery.data]);
  const summaryItems = normalized ? buildSummaryItems(kind, normalized.payload) : [];

  async function handleShare() {
    if (!normalized) {
      return;
    }
    try {
      if (normalized.imageUrl) {
        const suffix = kind === "daily" ? (params.date ?? "daily") : kind === "weekly" ? (params.startDate ?? "weekly") : (params.yearMonth ?? "monthly");
        const mode = await shareImageFile({
          title: normalized.title,
          text: normalized.subtitle,
          url: normalized.imageUrl,
          fileName: `familycut-${kind}-${suffix}.png`
        });
        setNotice(mode === "shared" ? "已打开系统分享。" : "当前浏览器不支持文件分享，已改为下载图片。");
        return;
      }
      setNotice("当前报表还没有可分享的图片。");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "分享失败。");
    }
  }

  async function handleExport() {
    if (!normalized?.imageUrl) {
      setNotice("当前报表还没有可导出的图片。");
      return;
    }
    try {
      const suffix = kind === "daily" ? (params.date ?? "daily") : kind === "weekly" ? (params.startDate ?? "weekly") : (params.yearMonth ?? "monthly");
      await downloadUrl(normalized.imageUrl, `familycut-${kind}-${suffix}.png`);
      setNotice("已开始导出图片。");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "导出失败。");
    }
  }

  return (
    <Screen
      title={normalized?.title ?? "报表详情"}
      subtitle={normalized?.subtitle ?? "正在加载长图与摘要…"}
      actions={
        <div className="screen-action-row">
          <button className="secondary-button" type="button" onClick={() => void handleExport()} disabled={!reportQuery.data}>
            导出
          </button>
          <button className="secondary-button secondary-button-muted" type="button" onClick={() => void handleShare()} disabled={!reportQuery.data}>
            分享
          </button>
        </div>
      }
    >
      {notice ? <p className="status-banner status-info">{notice}</p> : null}
      {reportQuery.isError ? (
        <p className="status-banner status-error">
          {reportQuery.error instanceof Error ? reportQuery.error.message : "报表加载失败。"}
        </p>
      ) : null}
      <section className="panel panel-hero">
        <div className="hero-panel-grid">
          <div className="hero-panel-primary">
            <p className="screen-eyebrow">{kind === "daily" ? "Daily" : kind === "weekly" ? "Weekly" : "Monthly"}</p>
            <h2>{normalized?.title ?? "报表详情"}</h2>
            <p className="panel-muted">{normalized?.subtitle ?? "正在加载报表摘要…"}</p>
          </div>
          <div className="hero-chip-row">
            {summaryItems.slice(0, 3).map((item) => (
              <span className="hero-chip" key={item.label}>
                {item.label} {item.value}
              </span>
            ))}
          </div>
        </div>
      </section>
      {normalized?.imageUrl ? (
        <a className="report-image-link" href={normalized.imageUrl} target="_blank" rel="noreferrer">
          <img className="report-image" src={normalized.imageUrl} alt={normalized.title} />
        </a>
      ) : (
        <div className="panel panel-muted">当前报表还没有生成长图。</div>
      )}

      <section className="panel">
        <div className="panel-header">
          <h2>摘要</h2>
          <span>关键指标</span>
        </div>
        {kind === "daily" && normalized?.payload["weight_source"] === "latest_measurement" ? (
          <p className="panel-muted">TDEE 按最近一次体重记录计算；额外运动消耗单独叠加到当日总 TDEE。</p>
        ) : null}
        <div className="summary-grid">
          {summaryItems.map((item) => (
            <article className="summary-item" key={item.label}>
              <strong>{item.label}</strong>
              <span>{item.value}</span>
            </article>
          ))}
        </div>
      </section>
    </Screen>
  );
}

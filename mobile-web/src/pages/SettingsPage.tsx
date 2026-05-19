import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { Screen } from "../components/Screen";
import { listMeasurements } from "../lib/api";
import { useAuth } from "../lib/auth";
import { clearOfflineData } from "../lib/offline";
import { calculateNutritionTargets } from "../lib/utils";

function calculateAge(birthYear: number | null | undefined): number | null {
  if (!birthYear) {
    return null;
  }
  return new Date().getFullYear() - birthYear;
}

function calculateBmr(input: {
  sex: string | null | undefined;
  birthYear: number | null | undefined;
  heightCm: number | null | undefined;
  weightKg: number | null | undefined;
}): number | null {
  if (!input.sex || !input.birthYear || !input.heightCm || !input.weightKg) {
    return null;
  }
  const age = calculateAge(input.birthYear);
  if (age === null) {
    return null;
  }
  const sexAdjustment = input.sex.toLowerCase() === "male" ? 5 : -161;
  return 10 * input.weightKg + 6.25 * input.heightCm - 5 * age + sexAdjustment;
}

function calculateTdee(bmr: number | null, activityFactor: number | null | undefined): number | null {
  if (bmr === null || !activityFactor) {
    return null;
  }
  return bmr * activityFactor;
}

export function SettingsPage() {
  const { member, session, logout } = useAuth();
  const [notice, setNotice] = useState("");
  const measurementsQuery = useQuery({
    queryKey: ["measurements"],
    queryFn: () => listMeasurements(session!.accessToken),
    enabled: Boolean(session?.accessToken)
  });
  const latestMeasurement = measurementsQuery.data?.[0];
  const latestWeightKg = latestMeasurement?.weight_kg ?? null;
  const age = calculateAge(member?.birth_year);
  const bmr = calculateBmr({
    sex: member?.sex,
    birthYear: member?.birth_year,
    heightCm: member?.height_cm,
    weightKg: latestWeightKg
  });
  const tdee = calculateTdee(bmr, member?.activity_factor);
  const nutritionTargets = calculateNutritionTargets({
    weightKg: latestWeightKg,
    tdee,
    goalDeficitKcal: member?.goal_deficit_kcal
  });

  async function handleClearOfflineData() {
    try {
      await clearOfflineData();
      setNotice("本地缓存已清理。");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "清理失败。");
    }
  }

  return (
    <Screen title="设置" subtitle="管理当前账号和本地缓存。">
      <section className="panel panel-hero">
        <div className="hero-panel-grid">
          <div className="hero-panel-primary">
            <p className="screen-eyebrow">Profile Hub</p>
            <h2>账号、资料与本地状态都在这里维护</h2>
            <p className="panel-muted">这里显示当前身体参数和 TDEE 估算，也能重新进入资料编辑。</p>
          </div>
          <div className="hero-chip-row">
            <span className="hero-chip">账号 {member?.username ?? "--"}</span>
            <span className="hero-chip">BMR {bmr !== null ? `${bmr.toFixed(0)} kcal` : "--"}</span>
            <span className="hero-chip">TDEE {tdee !== null ? `${tdee.toFixed(0)} kcal` : "--"}</span>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>当前账号</h2>
          <span>{member?.username ?? "--"}</span>
        </div>
        <div className="summary-grid">
          <article className="summary-item">
            <strong>年龄</strong>
            <span>{age !== null ? `${age} 岁` : "--"}</span>
          </article>
          <article className="summary-item">
            <strong>身高</strong>
            <span>{member?.height_cm ? `${member.height_cm} cm` : "--"}</span>
          </article>
          <article className="summary-item">
            <strong>活动系数</strong>
            <span>{member?.activity_factor ?? "--"}</span>
          </article>
          <article className="summary-item">
            <strong>最新体重</strong>
            <span>{latestWeightKg !== null ? `${latestWeightKg.toFixed(1)} kg` : "--"}</span>
          </article>
        </div>
        <ul className="detail-list">
          <li>显示名：{member?.display_name ?? "--"}</li>
          <li>性别：{member?.sex === "male" ? "男" : member?.sex === "female" ? "女" : "--"}</li>
          <li>年龄：{age !== null ? `${age} 岁` : "--"}</li>
          <li>身高：{member?.height_cm ? `${member.height_cm} cm` : "--"}</li>
          <li>活动系数：{member?.activity_factor ?? "--"}</li>
          <li>最新体重：{latestWeightKg !== null ? `${latestWeightKg.toFixed(1)} kg` : "--"}</li>
          <li>单位偏好：{member?.unit_preference ?? "--"}</li>
          <li>目标热量差：{member?.goal_deficit_kcal ?? "--"} kcal</li>
        </ul>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>TDEE 估算</h2>
          <span>按最新体重</span>
        </div>
        <div className="summary-grid">
          <article className="summary-item">
            <strong>基础代谢</strong>
            <span>{bmr !== null ? `${bmr.toFixed(0)} kcal` : "--"}</span>
          </article>
          <article className="summary-item">
            <strong>静态 TDEE</strong>
            <span>{tdee !== null ? `${tdee.toFixed(0)} kcal` : "--"}</span>
          </article>
        </div>
        <ul className="detail-list">
          <li>基础代谢 BMR：{bmr !== null ? `${bmr.toFixed(0)} kcal` : "--"}</li>
          <li>静态 TDEE：{tdee !== null ? `${tdee.toFixed(0)} kcal` : "--"}</li>
        </ul>
        <p className="panel-muted">
          这里按最新体重、性别、年龄、身高和活动系数估算，不含额外运动消耗。
          {bmr === null ? " 当前资料或体重还不完整，所以暂时无法计算。" : ""}
        </p>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>每日摄入目标</h2>
          <span>按最新体重动态重算</span>
        </div>
        {nutritionTargets ? (
          <>
            <div className="summary-grid">
              <article className="summary-item">
                <strong>目标摄入</strong>
                <span>{nutritionTargets.intakeKcal.toFixed(0)} kcal</span>
              </article>
              <article className="summary-item">
                <strong>碳水</strong>
                <span>{nutritionTargets.carbG.toFixed(1)} g · {nutritionTargets.carbPct.toFixed(1)}%</span>
              </article>
              <article className="summary-item">
                <strong>蛋白质</strong>
                <span>{nutritionTargets.proteinG.toFixed(1)} g · {nutritionTargets.proteinPct.toFixed(1)}%</span>
              </article>
              <article className="summary-item">
                <strong>脂肪</strong>
                <span>{nutritionTargets.fatG.toFixed(1)} g · {nutritionTargets.fatPct.toFixed(1)}%</span>
              </article>
            </div>
            <p className="panel-muted">输入新的体重后，这里的 BMR、TDEE 和每日碳水/蛋白质/脂肪目标会随之更新。</p>
          </>
        ) : (
          <p className="panel-muted">补齐性别、出生年份、身高，并至少录入一条体重后，这里才会生成每日摄入目标。</p>
        )}
      </section>

      {notice ? <p className="status-banner status-info">{notice}</p> : null}

      <section className="panel">
        <div className="panel-header">
          <h2>操作</h2>
          <span>账户与缓存</span>
        </div>
        <div className="button-stack">
          <Link className="secondary-button" to="/profile/setup">
            编辑基础资料
          </Link>
          <button className="secondary-button" type="button" onClick={() => void handleClearOfflineData()}>
            清理本地缓存
          </button>
          <button className="primary-button" type="button" onClick={logout}>
            退出登录
          </button>
        </div>
      </section>
    </Screen>
  );
}

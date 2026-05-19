import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Screen } from "../components/Screen";
import { updateCurrentMember } from "../lib/api";
import { isProfileComplete, useAuth } from "../lib/auth";
import { joinMealSlots } from "../lib/utils";

export function ProfileSetupPage() {
  const navigate = useNavigate();
  const { session, member, updateMember } = useAuth();
  const editingExistingProfile = isProfileComplete(member);
  const [displayName, setDisplayName] = useState("");
  const [sex, setSex] = useState("female");
  const [birthYear, setBirthYear] = useState("1995");
  const [heightCm, setHeightCm] = useState("165");
  const [activityFactor, setActivityFactor] = useState("1.4");
  const [goalDeficitKcal, setGoalDeficitKcal] = useState("500");
  const [unitPreference, setUnitPreference] = useState("metric");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!member) {
      return;
    }
    setDisplayName(member.display_name ?? "");
    setSex(member.sex ?? "female");
    setBirthYear(member.birth_year ? String(member.birth_year) : "1995");
    setHeightCm(member.height_cm ? String(member.height_cm) : "165");
    setActivityFactor(String(member.activity_factor));
    setGoalDeficitKcal(String(member.goal_deficit_kcal));
    setUnitPreference(member.unit_preference);
  }, [member]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session?.accessToken) {
      return;
    }
    setBusy(true);
    setNotice("");
    try {
      const nextMember = await updateCurrentMember(session.accessToken, {
        display_name: displayName,
        sex,
        birth_year: Number(birthYear),
        height_cm: Number(heightCm),
        activity_factor: Number(activityFactor),
        goal_deficit_kcal: Number(goalDeficitKcal),
        unit_preference: unitPreference
      });
      updateMember(nextMember);
      navigate(editingExistingProfile ? "/settings" : "/home", { replace: true });
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "资料保存失败。");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen
      title={editingExistingProfile ? "基础资料" : "补齐资料"}
      subtitle={editingExistingProfile ? "更新基础资料后，TDEE 和报表会按最新资料重算。" : "完善基础资料后，报表和热量计算会更准确。"}
      eyebrow={editingExistingProfile ? "Profile" : "First Setup"}
    >
      <div className="panel panel-hero">
        <div className="hero-panel-grid">
          <div className="hero-panel-primary">
            <p className="screen-eyebrow">{editingExistingProfile ? "Profile Sheet" : "First Setup"}</p>
            <h2>{editingExistingProfile ? "维护长期资料" : "先把基础资料补完整"}</h2>
            <p className="panel-muted">当前餐次槽位：{member ? joinMealSlots(member.meal_slots) : "--"}</p>
          </div>
          <div className="hero-chip-row">
            <span className="hero-chip">活动系数 {activityFactor}</span>
            <span className="hero-chip">目标缺口 {goalDeficitKcal} kcal</span>
            <span className="hero-chip">单位 {unitPreference === "metric" ? "公制" : "英制"}</span>
          </div>
        </div>
      </div>
      <section className="panel">
        <div className="panel-header">
          <h2>填写提醒</h2>
          <span>先固定长期参数</span>
        </div>
        <div className="summary-grid">
          <article className="summary-item">
            <strong>性别</strong>
            <span>{member?.sex ? "首次设置后锁定，用于 TDEE" : "本次可设置，用于 TDEE"}</span>
          </article>
          <article className="summary-item">
            <strong>出生年份</strong>
            <span>{member?.birth_year ? "首次设置后锁定，用于年龄/TDEE" : "本次可设置，用于年龄/TDEE"}</span>
          </article>
          <article className="summary-item">
            <strong>活动系数</strong>
            <span>后续可调整</span>
          </article>
          <article className="summary-item">
            <strong>目标缺口</strong>
            <span>后续可调整</span>
          </article>
        </div>
      </section>
      <form className="stack-form" onSubmit={handleSubmit}>
        <label className="field">
          <span>显示名</span>
          <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} required />
        </label>
        <label className="field">
          <span>性别</span>
          <select value={sex} onChange={(event) => setSex(event.target.value)} disabled={Boolean(member?.sex)}>
            <option value="female">女</option>
            <option value="male">男</option>
          </select>
        </label>
        <label className="field">
          <span>出生年份</span>
          <input
            type="number"
            min="1900"
            max="2100"
            value={birthYear}
            onChange={(event) => setBirthYear(event.target.value)}
            disabled={Boolean(member?.birth_year)}
            required
          />
        </label>
        <label className="field">
          <span>身高 cm</span>
          <input type="number" value={heightCm} onChange={(event) => setHeightCm(event.target.value)} required />
        </label>
        <label className="field">
          <span>活动系数</span>
          <input type="number" step="0.1" value={activityFactor} onChange={(event) => setActivityFactor(event.target.value)} required />
        </label>
        <label className="field">
          <span>目标热量差 kcal</span>
          <input type="number" value={goalDeficitKcal} onChange={(event) => setGoalDeficitKcal(event.target.value)} required />
        </label>
        <label className="field">
          <span>单位偏好</span>
          <select value={unitPreference} onChange={(event) => setUnitPreference(event.target.value)}>
            <option value="metric">公制</option>
            <option value="imperial">英制</option>
          </select>
        </label>
        {notice ? <p className="status-banner status-error">{notice}</p> : null}
        <button className="primary-button" type="submit" disabled={busy}>
          {busy ? "保存中…" : editingExistingProfile ? "保存资料" : "保存并进入首页"}
        </button>
      </form>
    </Screen>
  );
}

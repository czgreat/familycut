import { useEffect, useState } from "react";

import {
  createMemberInvitation,
  fetchInvitationHistory,
  fetchMemberDetail,
  fetchMemberSummaries,
  InvitationHistoryItem,
  InvitationResponse,
  MemberDetail,
  MemberSummary
} from "../lib/api";

type MembersPageProps = {
  token: string;
};

export function MembersPage({ token }: MembersPageProps) {
  const [members, setMembers] = useState<MemberSummary[]>([]);
  const [invitations, setInvitations] = useState<InvitationHistoryItem[]>([]);
  const [selectedMemberId, setSelectedMemberId] = useState<string>("");
  const [selectedMember, setSelectedMember] = useState<MemberDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [invite, setInvite] = useState<InvitationResponse | null>(null);
  const [status, setStatus] = useState("正在读取成员数据...");

  useEffect(() => {
    Promise.all([fetchMemberSummaries(token), fetchInvitationHistory(token)])
      .then(([memberPayload, invitationPayload]) => {
        setMembers(memberPayload);
        setInvitations(invitationPayload);
        const firstMemberId = memberPayload[0]?.id ?? "";
        setSelectedMemberId((current) => current || firstMemberId)
        setStatus(memberPayload.length > 0 ? "已读取成员数据。" : "当前还没有成员数据。");
      })
      .catch((error) => {
        setStatus(error instanceof Error ? error.message : "读取成员数据失败。");
      });
  }, [token]);

  useEffect(() => {
    if (!selectedMemberId) {
      setSelectedMember(null);
      return;
    }
    fetchMemberDetail(token, selectedMemberId)
      .then(setSelectedMember)
      .catch((error) => {
        setStatus(error instanceof Error ? error.message : "读取成员详情失败。");
      });
  }, [token, selectedMemberId]);

  async function handleCreateInvitation() {
    setBusy(true);
    try {
      const payload = await createMemberInvitation(token);
      setInvite(payload);
      const invitationPayload = await fetchInvitationHistory(token);
      setInvitations(invitationPayload);
      setStatus("邀请码已生成。");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "生成邀请码失败。");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <section className="card dashboard-hero">
        <div className="dashboard-hero-copy">
          <p className="eyebrow">Members</p>
          <h2>先看成员，再看每个人最近的体重、餐食、运动和日报</h2>
          <p className="dashboard-hero-note">邀请码和成员详情都放在同一页，避免在后台来回跳转。</p>
        </div>
        <div className="hero-chip-row hero-chip-row-admin">
          <span className="hero-chip">成员 {members.length}</span>
          <span className="hero-chip">邀请码 {invitations.length}</span>
          <span className="hero-chip">{selectedMember ? `当前 ${selectedMember.display_name}` : "未选成员"}</span>
        </div>
      </section>

      <section className="section">
        <div className="section-header">
          <div>
            <p className="eyebrow">成员</p>
            <h2>家庭成员数据</h2>
          </div>
          <button className="primary-button" type="button" onClick={handleCreateInvitation} disabled={busy}>
            {busy ? "生成中..." : "生成邀请码"}
          </button>
        </div>

        {invite ? (
          <article className="card invite-card">
            <h3>最新邀请码</h3>
            <p className="invite-code">{invite.code}</p>
            <p>角色：{invite.role}</p>
          </article>
        ) : null}

        <p className={status.includes("失败") ? "status-line status-error page-banner" : "status-line page-banner"}>{status}</p>

        <section className="dashboard-mini-grid-admin">
          <article className="card dashboard-spotlight-card">
            <p className="eyebrow">成员数</p>
            <strong>{members.length}</strong>
            <span>当前家庭已加入成员</span>
          </article>
          <article className="card dashboard-spotlight-card">
            <p className="eyebrow">邀请码数</p>
            <strong>{invitations.length}</strong>
            <span>{invite ? `最新 ${invite.code}` : "可随时生成新的邀请码"}</span>
          </article>
          <article className="card dashboard-spotlight-card">
            <p className="eyebrow">当前详情</p>
            <strong>{selectedMember?.display_name ?? "未选成员"}</strong>
            <span>{selectedMember ? `最近日报 ${selectedMember.latest_report_date ?? "暂无"}` : "先从左侧选择成员"}</span>
          </article>
        </section>

        <div className="member-layout">
          <div className="member-list">
            {members.map((member) => (
              <button
                key={member.id}
                type="button"
                className={member.id === selectedMemberId ? "member-list-item member-list-item-active" : "member-list-item"}
                onClick={() => setSelectedMemberId(member.id)}
              >
                <strong>{member.display_name}</strong>
                <span>{member.username}</span>
                <span>{member.latest_weight_kg ? `${member.latest_weight_kg} kg` : "暂无体重"}</span>
              </button>
            ))}
          </div>

          {selectedMember ? (
            <article className="card member-detail-card">
              <h3>{selectedMember.display_name}</h3>
              <div className="member-summary-grid">
                <p>账号：{selectedMember.username}</p>
                <p>角色：{selectedMember.role === "admin" ? "管理员" : "成员"}</p>
                <p>身高：{selectedMember.height_cm ? `${selectedMember.height_cm} cm` : "未填写"}</p>
                <p>餐次：{selectedMember.meal_slots.join(" / ")}</p>
                <p>目标缺口：{selectedMember.goal_deficit_kcal} kcal</p>
                <p>最近体重：{selectedMember.latest_weight_kg ? `${selectedMember.latest_weight_kg} kg` : "暂无"}</p>
                <p>最近体脂：{selectedMember.latest_body_fat_pct ? `${selectedMember.latest_body_fat_pct}%` : "暂无"}</p>
                <p>最近日报：{selectedMember.latest_report_date ?? "暂无"}</p>
              </div>
              <div className="hero-chip-row hero-chip-row-admin">
                <span className="hero-chip">体重记录 {selectedMember.measurement_count}</span>
                <span className="hero-chip">餐食记录 {selectedMember.meal_count}</span>
                <span className="hero-chip">日报 {selectedMember.report_count}</span>
              </div>

              <div className="history-grid">
                <section className="card history-card">
                  <h4>最近体重</h4>
                  {selectedMember.recent_measurements.length > 0 ? (
                    selectedMember.recent_measurements.map((item) => (
                      <p key={item.measured_at}>
                        {new Date(item.measured_at).toLocaleDateString("zh-CN")}：
                        {item.weight_kg} kg
                        {item.body_fat_pct ? ` / ${item.body_fat_pct}%` : ""}
                      </p>
                    ))
                  ) : (
                    <p>暂无体重记录。</p>
                  )}
                </section>

                <section className="card history-card">
                  <h4>最近餐食</h4>
                  {selectedMember.recent_meals.length > 0 ? (
                    selectedMember.recent_meals.map((item) => (
                      <p key={item.consumed_at}>
                        {new Date(item.consumed_at).toLocaleDateString("zh-CN")}：
                        {item.meal_slot} / {item.food_name} / {Math.round(item.actual_grams)} g / {Math.round(item.kcal)} kcal
                      </p>
                    ))
                  ) : (
                    <p>暂无餐食记录。</p>
                  )}
                </section>

                <section className="card history-card">
                  <h4>最近运动</h4>
                  {selectedMember.recent_exercises.length > 0 ? (
                    selectedMember.recent_exercises.map((item) => (
                      <p key={item.occurred_at}>
                        {new Date(item.occurred_at).toLocaleDateString("zh-CN")}：
                        {item.exercise_type}
                        {item.distance_km ? ` / ${item.distance_km} km` : ""}
                        {item.duration_min ? ` / ${item.duration_min} 分钟` : ""}
                        {item.estimated_kcal ? ` / ${Math.round(item.estimated_kcal)} kcal` : ""}
                      </p>
                    ))
                  ) : (
                    <p>暂无运动记录。</p>
                  )}
                </section>

                <section className="card history-card">
                  <h4>最近日报</h4>
                  {selectedMember.recent_reports.length > 0 ? (
                    selectedMember.recent_reports.map((item) => (
                      <p key={item.report_date}>
                        {item.report_date}：
                        {item.deficit_kcal ?? "暂无缺口"} kcal
                        {item.deficit_hit ? " / 达标" : " / 未达标"}
                        {item.carb_g !== null ? ` / 碳水 ${Math.round(item.carb_g)}g` : ""}
                        {item.fat_g !== null ? ` / 脂肪 ${Math.round(item.fat_g)}g` : ""}
                        {item.protein_g !== null ? ` / 蛋白质 ${Math.round(item.protein_g)}g` : ""}
                      </p>
                    ))
                  ) : (
                    <p>暂无日报记录。</p>
                  )}
                </section>
              </div>

              <section className="card history-card">
                <h4>日报营养摘要</h4>
                {selectedMember.recent_reports.length > 0 ? (
                  selectedMember.recent_reports.slice(0, 3).map((item) => (
                    <p key={`macro-${item.report_date}`}>
                      {item.report_date}：
                      {item.carb_g !== null ? ` 碳水 ${Math.round(item.carb_g)}g` : " 碳水暂无"}
                      {item.fat_g !== null ? ` / 脂肪 ${Math.round(item.fat_g)}g` : " / 脂肪暂无"}
                      {item.protein_g !== null ? ` / 蛋白质 ${Math.round(item.protein_g)}g` : " / 蛋白质暂无"}
                    </p>
                  ))
                ) : (
                  <p>当前还没有日报记录可供汇总。</p>
                )}
              </section>
            </article>
          ) : (
            <article className="card member-detail-card">
              <p>当前还没有可展示的成员。</p>
            </article>
          )}
        </div>

        <section className="section">
          <div className="section-header">
            <div>
              <p className="eyebrow">邀请记录</p>
              <h2>历史邀请码</h2>
            </div>
          </div>
          <div className="table-card">
            <p className="table-caption">邀请码生成后立即可用；这里保留创建时间和使用状态，方便追查成员加入历史。</p>
            <table>
              <thead>
                <tr>
                  <th>邀请码</th>
                  <th>角色</th>
                  <th>创建时间</th>
                  <th>使用状态</th>
                </tr>
              </thead>
              <tbody>
                {invitations.map((item) => (
                  <tr key={item.id}>
                    <td>{item.code}</td>
                    <td>{item.role}</td>
                    <td>{new Date(item.created_at).toLocaleString("zh-CN")}</td>
                    <td>{item.used_at ? `已使用：${new Date(item.used_at).toLocaleString("zh-CN")}` : "未使用"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </section>
    </div>
  );
}

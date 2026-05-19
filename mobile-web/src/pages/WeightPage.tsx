import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Screen } from "../components/Screen";
import { createMeasurement, listMeasurements } from "../lib/api";
import { useAuth } from "../lib/auth";
import { clearWeightDraft, loadWeightDraft, saveWeightDraft } from "../lib/offline";
import { formatDateTime, toDateTimeLocalValue, toIsoString } from "../lib/utils";

export function WeightPage() {
  const queryClient = useQueryClient();
  const { session } = useAuth();
  const [measuredAt, setMeasuredAt] = useState(toDateTimeLocalValue(new Date()));
  const [weightKg, setWeightKg] = useState("");
  const [bodyFatPct, setBodyFatPct] = useState("");
  const [note, setNote] = useState("");
  const [notice, setNotice] = useState("");

  const measurementsQuery = useQuery({
    queryKey: ["measurements"],
    queryFn: () => listMeasurements(session!.accessToken),
    enabled: Boolean(session?.accessToken)
  });

  useEffect(() => {
    void loadWeightDraft().then((draft) => {
      if (!draft) {
        return;
      }
      setMeasuredAt(draft.measuredAt);
      setWeightKg(draft.weightKg);
      setBodyFatPct(draft.bodyFatPct);
      setNote(draft.note);
    });
  }, []);

  useEffect(() => {
    void saveWeightDraft({
      measuredAt,
      weightKg,
      bodyFatPct,
      note
    });
  }, [bodyFatPct, measuredAt, note, weightKg]);

  const mutation = useMutation({
    mutationFn: async () =>
      createMeasurement(session!.accessToken, {
        measured_at: toIsoString(measuredAt),
        weight_kg: Number(weightKg),
        body_fat_pct: bodyFatPct ? Number(bodyFatPct) : undefined,
        note: note || undefined
      }),
    onSuccess: async () => {
      setNotice("晨重已保存。");
      setMeasuredAt(toDateTimeLocalValue(new Date()));
      setWeightKg("");
      setBodyFatPct("");
      setNote("");
      await clearWeightDraft();
      await queryClient.invalidateQueries({ queryKey: ["measurements"] });
    },
    onError: (error) => {
      setNotice(error instanceof Error ? error.message : "晨重保存失败。");
    }
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("");
    mutation.mutate();
  }

  return (
    <Screen title="晨重记录" subtitle="记录今天的体重和体脂，表单会自动保存草稿。">
      <section className="panel panel-hero">
        <div className="hero-panel-grid">
          <div className="hero-panel-primary">
            <p className="screen-eyebrow">Morning Check</p>
            <h2>把晨重固定成每天第一步</h2>
            <p className="panel-muted">体重越稳定地记录，TDEE 和日报解释就越可靠。</p>
          </div>
          <div className="hero-chip-row">
            <span className="hero-chip">最近记录 {measurementsQuery.data?.length ?? 0} 条</span>
            <span className="hero-chip">草稿自动保存</span>
          </div>
        </div>
      </section>

      <form className="panel stack-form" onSubmit={handleSubmit}>
        <label className="field">
          <span>记录时间</span>
          <input type="datetime-local" value={measuredAt} onChange={(event) => setMeasuredAt(event.target.value)} required />
        </label>
        <label className="field">
          <span>体重 kg</span>
          <input type="number" step="0.1" value={weightKg} onChange={(event) => setWeightKg(event.target.value)} required />
        </label>
        <label className="field">
          <span>体脂 %</span>
          <input type="number" step="0.1" value={bodyFatPct} onChange={(event) => setBodyFatPct(event.target.value)} />
        </label>
        <label className="field">
          <span>备注</span>
          <textarea rows={3} value={note} onChange={(event) => setNote(event.target.value)} />
        </label>
        {notice ? <p className={mutation.isError ? "status-banner status-error" : "status-banner status-success"}>{notice}</p> : null}
        <button className="primary-button" type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "保存中…" : "保存晨重"}
        </button>
      </form>

      <section className="panel">
        <div className="panel-header">
          <h2>最近记录</h2>
          <span>{measurementsQuery.data?.length ?? 0} 条</span>
        </div>
        <div className="timeline">
          {(measurementsQuery.data ?? []).map((item) => (
            <article className="timeline-item" key={item.id}>
              <strong>{item.weight_kg.toFixed(1)} kg</strong>
              <span>
                {item.body_fat_pct ? `${item.body_fat_pct.toFixed(1)}%` : "未填体脂"} · {formatDateTime(item.measured_at)}
              </span>
            </article>
          ))}
        </div>
      </section>
    </Screen>
  );
}

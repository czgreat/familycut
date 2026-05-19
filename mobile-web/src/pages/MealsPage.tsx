import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Screen } from "../components/Screen";
import { NutritionDraft, createMeal, createNutritionDraft, fetchDailyReport, getNutritionDraft, listMeals } from "../lib/api";
import { useAuth } from "../lib/auth";
import {
  clearMealDraft,
  clearPendingNutritionDraft,
  loadMealDraft,
  loadPendingNutritionDraft,
  saveMealDraft,
  savePendingNutritionDraft
} from "../lib/offline";
import { currentDateTimeLocalValue, formatDateTime, getTodayDate, macroPercentages, per100Value, toDateTimeLocalValue, toIsoString } from "../lib/utils";

type DraftType = "label" | "dish_estimate";

const mealSlotLabels: Record<string, string> = {
  breakfast: "早餐",
  lunch: "午餐",
  dinner: "晚餐",
  snack: "加餐"
};

const weightScopeLabels: Record<string, string> = {
  solid_only: "只算固形物",
  includes_liquid: "包含汤汁/液体",
  liquid_only: "只算液体",
  unclear: "口径不明确"
};

function weightScopeLabel(scope: string | null | undefined): string {
  if (!scope) {
    return "未说明";
  }
  return weightScopeLabels[scope] ?? scope;
}

function formatDraftWeightBreakdown(draft: NutritionDraft): string {
  const parts: string[] = [];
  if (typeof draft.estimated_solid_grams === "number") {
    parts.push(`固形物 ${draft.estimated_solid_grams.toFixed(0)} g`);
  }
  if (typeof draft.estimated_liquid_grams === "number") {
    parts.push(`汤汁/液体 ${draft.estimated_liquid_grams.toFixed(0)} g`);
  }
  if (typeof draft.estimated_grams === "number") {
    parts.push(`总量 ${draft.estimated_grams.toFixed(0)} g`);
  }
  return parts.length > 0 ? parts.join(" · ") : "这次没有返回结构化重量拆分。";
}

function macroStatusLabel(status: string | null | undefined): string {
  switch (status) {
    case "on_target":
      return "达标";
    case "low":
      return "偏低";
    case "high":
      return "偏高";
    default:
      return "待计算";
  }
}

export function MealsPage() {
  const queryClient = useQueryClient();
  const { session } = useAuth();
  const today = getTodayDate();
  const labelCameraInputRef = useRef<HTMLInputElement | null>(null);
  const labelLibraryInputRef = useRef<HTMLInputElement | null>(null);
  const dishCameraInputRef = useRef<HTMLInputElement | null>(null);
  const dishLibraryInputRef = useRef<HTMLInputElement | null>(null);
  const [mealSlot, setMealSlot] = useState("breakfast");
  const [consumedAt, setConsumedAt] = useState(currentDateTimeLocalValue());
  const [foodName, setFoodName] = useState("");
  const [actualGrams, setActualGrams] = useState("");
  const [per100Kcal, setPer100Kcal] = useState("");
  const [per100Carb, setPer100Carb] = useState("");
  const [per100Fat, setPer100Fat] = useState("");
  const [per100Protein, setPer100Protein] = useState("");
  const [per100Sodium, setPer100Sodium] = useState("");
  const [dishHint, setDishHint] = useState("");
  const [draftId, setDraftId] = useState("");
  const [draftType, setDraftType] = useState<DraftType | null>(null);
  const [statusText, setStatusText] = useState("");
  const [notice, setNotice] = useState("");

  const recentMealsQuery = useQuery({
    queryKey: ["meals", "recent"],
    queryFn: () => listMeals(session!.accessToken),
    enabled: Boolean(session?.accessToken)
  });

  const todayReportQuery = useQuery({
    queryKey: ["report", "daily", today],
    queryFn: () => fetchDailyReport(session!.accessToken, today),
    enabled: Boolean(session?.accessToken)
  });

  useEffect(() => {
    void loadMealDraft().then((draft) => {
      if (!draft) {
        return;
      }
      setMealSlot(draft.mealSlot);
      setConsumedAt(draft.consumedAt);
      setFoodName(draft.foodName);
      setActualGrams(draft.actualGrams);
      setPer100Kcal(draft.per100Kcal);
      setPer100Carb(draft.per100Carb);
      setPer100Fat(draft.per100Fat);
      setPer100Protein(draft.per100Protein);
      setPer100Sodium(draft.per100Sodium);
      setDishHint(draft.dishHint);
      setDraftId(draft.draftId);
    });
    void loadPendingNutritionDraft().then((draft) => {
      if (!draft) {
        return;
      }
      setDraftId(draft.draftId);
      setDraftType(draft.draftType as DraftType);
      setStatusText("正在恢复上次识别状态…");
    });
  }, []);

  useEffect(() => {
    void saveMealDraft({
      mealSlot,
      consumedAt,
      foodName,
      actualGrams,
      per100Kcal,
      per100Carb,
      per100Fat,
      per100Protein,
      per100Sodium,
      draftId,
      dishHint
    });
  }, [actualGrams, consumedAt, dishHint, draftId, foodName, mealSlot, per100Carb, per100Fat, per100Kcal, per100Protein, per100Sodium]);

  const uploadMutation = useMutation({
    mutationFn: async ({ file, nextDraftType }: { file: File; nextDraftType: DraftType }) =>
      createNutritionDraft(session!.accessToken, file, nextDraftType, nextDraftType === "dish_estimate" ? dishHint : undefined),
    onSuccess: async (payload, variables) => {
      setDraftId(payload.id);
      setDraftType(variables.nextDraftType);
      setStatusText("图片已上传，正在等待服务端识别…");
      setNotice("");
      await savePendingNutritionDraft({
        draftId: payload.id,
        draftType: variables.nextDraftType
      });
    },
    onError: (error) => {
      setNotice(error instanceof Error ? error.message : "图片上传失败。");
    }
  });

  const draftQuery = useQuery({
    queryKey: ["nutrition-draft", draftId],
    queryFn: () => getNutritionDraft(session!.accessToken, draftId),
    enabled: Boolean(session?.accessToken && draftId),
    refetchInterval: (query) => {
      const nextData = query.state.data;
      return nextData?.status === "processing" ? 1500 : false;
    }
  });

  useEffect(() => {
    if (!draftQuery.data) {
      return;
    }

    if (draftQuery.data.status === "processing") {
      setStatusText(`正在识别${draftType === "dish_estimate" ? "饭菜" : "营养表"}…`);
      return;
    }

    if (draftQuery.data.status === "failed") {
      setStatusText(draftQuery.data.error_message ?? "识别失败，请重试。");
      setDishHint("");
      void clearPendingNutritionDraft();
      return;
    }

    setStatusText("识别完成，可以确认并落单。");
    setFoodName(draftQuery.data.food_name ?? foodName);
    setDraftId(draftQuery.data.id);
    setPer100Kcal(draftQuery.data.per_100g_kcal?.toFixed(1) ?? per100Kcal);
    setPer100Carb(draftQuery.data.per_100g_carb_g?.toFixed(1) ?? per100Carb);
    setPer100Fat(draftQuery.data.per_100g_fat_g?.toFixed(1) ?? per100Fat);
    setPer100Protein(draftQuery.data.per_100g_protein_g?.toFixed(1) ?? per100Protein);
    setPer100Sodium(draftQuery.data.per_100g_sodium_mg?.toFixed(1) ?? per100Sodium);
    if (draftQuery.data.estimated_grams && !actualGrams) {
      setActualGrams(draftQuery.data.estimated_grams.toFixed(0));
    }
    setDishHint("");
    void clearPendingNutritionDraft();
  }, [actualGrams, draftQuery.data, draftType, foodName, per100Carb, per100Fat, per100Kcal, per100Protein, per100Sodium]);

  const createMealMutation = useMutation({
    mutationFn: async () => {
      const grams = Number(actualGrams);
      const ratio = grams / 100;
      return createMeal(session!.accessToken, {
        draft_id: draftId || undefined,
        meal_slot: mealSlot,
        consumed_at: toIsoString(consumedAt),
        food_name: foodName,
        actual_grams: grams,
        kcal: Number(per100Kcal) * ratio,
        carb_g: (Number(per100Carb) || 0) * ratio,
        fat_g: (Number(per100Fat) || 0) * ratio,
        protein_g: (Number(per100Protein) || 0) * ratio,
        sodium_mg: per100Sodium ? Number(per100Sodium) * ratio : undefined,
        corrections: draftType
          ? {
              draft_type: draftType
            }
          : undefined
      });
    },
    onSuccess: async () => {
      setNotice("餐食已保存。");
      setConsumedAt(currentDateTimeLocalValue());
      setFoodName("");
      setActualGrams("");
      setPer100Kcal("");
      setPer100Carb("");
      setPer100Fat("");
      setPer100Protein("");
      setPer100Sodium("");
      setDishHint("");
      setDraftId("");
      setDraftType(null);
      setStatusText("");
      await clearMealDraft();
      await clearPendingNutritionDraft();
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["meals"] }),
        queryClient.invalidateQueries({ queryKey: ["reports", "recent"] }),
        queryClient.invalidateQueries({ queryKey: ["report", "daily", today] })
      ]);
    },
    onError: (error) => {
      setNotice(error instanceof Error ? error.message : "餐食保存失败。");
    }
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("");
    createMealMutation.mutate();
  }

  async function handleSelectImage(event: ChangeEvent<HTMLInputElement>, nextDraftType: DraftType) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    await uploadMutation.mutateAsync({ file, nextDraftType });
    event.target.value = "";
  }

  function applyMeal(mealId: string) {
    const item = recentMealsQuery.data?.find((meal) => meal.id === mealId);
    if (!item) {
      return;
    }
    setMealSlot(item.meal_slot);
    setConsumedAt(toDateTimeLocalValue(new Date()));
    setFoodName(item.food_name);
    setActualGrams(item.actual_grams.toString());
    setPer100Kcal(per100Value(item.kcal, item.actual_grams));
    setPer100Carb(per100Value(item.carb_g, item.actual_grams));
    setPer100Fat(per100Value(item.fat_g, item.actual_grams));
    setPer100Protein(per100Value(item.protein_g, item.actual_grams));
    setPer100Sodium(per100Value(item.sodium_mg ?? null, item.actual_grams));
    setDraftId(item.draft_id ?? "");
    setDraftType((item.draft_type as DraftType | null) ?? null);
    setStatusText("已把历史餐食复制到编辑区。");
  }

  function useCurrentTime() {
    setConsumedAt(currentDateTimeLocalValue());
  }

  const totalKcalPreview = useMemo(() => {
    const grams = Number(actualGrams);
    const kcal = Number(per100Kcal);
    if (!grams || Number.isNaN(grams) || Number.isNaN(kcal)) {
      return "--";
    }
    return (kcal * (grams / 100)).toFixed(0);
  }, [actualGrams, per100Kcal]);

  const macroPreview = useMemo(() => {
    const grams = Number(actualGrams);
    const carbPer100 = Number(per100Carb);
    const fatPer100 = Number(per100Fat);
    const proteinPer100 = Number(per100Protein);
    if (!grams || Number.isNaN(grams)) {
      return null;
    }
    const ratio = grams / 100;
    const carbG = Number.isNaN(carbPer100) ? 0 : carbPer100 * ratio;
    const fatG = Number.isNaN(fatPer100) ? 0 : fatPer100 * ratio;
    const proteinG = Number.isNaN(proteinPer100) ? 0 : proteinPer100 * ratio;
    const percentages = macroPercentages({ carbG, fatG, proteinG });
    return {
      carbG,
      fatG,
      proteinG,
      ...percentages
    };
  }, [actualGrams, per100Carb, per100Fat, per100Protein]);

  const todayMacroStatus = todayReportQuery.data?.payload?.macro_status as
    | Record<string, { actual_g?: number; target_g?: number; progress_pct?: number; status?: string; remaining_g?: number; excess_g?: number }>
    | undefined;
  const todayMacroTarget = todayReportQuery.data?.payload?.macro_target as
    | Record<string, number | undefined>
    | undefined;
  const todayPayload = todayReportQuery.data?.payload as Record<string, unknown> | undefined;

  return (
    <Screen title="餐食记录" subtitle="支持手动记餐、营养成分表识别和现成饭菜估算。">
      <input
        ref={labelCameraInputRef}
        className="hidden-input"
        type="file"
        accept="image/*"
        capture="environment"
        onChange={(event) => void handleSelectImage(event, "label")}
      />
      <input
        ref={labelLibraryInputRef}
        className="hidden-input"
        type="file"
        accept="image/*"
        onChange={(event) => void handleSelectImage(event, "label")}
      />
      <input
        ref={dishCameraInputRef}
        className="hidden-input"
        type="file"
        accept="image/*"
        capture="environment"
        onChange={(event) => void handleSelectImage(event, "dish_estimate")}
      />
      <input
        ref={dishLibraryInputRef}
        className="hidden-input"
        type="file"
        accept="image/*"
        onChange={(event) => void handleSelectImage(event, "dish_estimate")}
      />

      <div className="panel panel-hero">
        <div className="hero-copy">
          <div>
            <p className="screen-eyebrow">AI Capture</p>
            <h2>先拍照，再确认每 100g 营养</h2>
          </div>
        </div>
        <div className="hero-chip-row">
          <span className="hero-chip">当前餐次 {mealSlotLabels[mealSlot]}</span>
          <span className="hero-chip">总热量预估 {totalKcalPreview} kcal</span>
          <span className="hero-chip">{draftType === "dish_estimate" ? "饭菜估算" : draftType === "label" ? "成分表识别" : "待选择识别方式"}</span>
        </div>
        <div className={statusText ? "hero-status hero-status-active" : "hero-status"}>
          <span className="hero-status-label">识别状态</span>
          <strong className="hero-status-text">{statusText || "待上传，支持拍照和相册导入。"}</strong>
        </div>
        <div className="capture-grid">
          <section className="capture-card">
            <div className="capture-card-copy">
              <p className="capture-card-kicker">营养成分表</p>
              <strong>拍包装或本地相册图片</strong>
            </div>
            <div className="capture-card-actions">
              <button
                className="secondary-button"
                type="button"
                onClick={() => labelCameraInputRef.current?.click()}
                disabled={uploadMutation.isPending}
              >
                {uploadMutation.isPending && draftType === "label" ? "上传中…" : "拍照识别"}
              </button>
              <button
                className="secondary-button secondary-button-muted"
                type="button"
                onClick={() => labelLibraryInputRef.current?.click()}
                disabled={uploadMutation.isPending}
              >
                相册导入
              </button>
            </div>
          </section>
          <section className="capture-card">
            <div className="capture-card-copy">
              <p className="capture-card-kicker">现成饭菜</p>
              <strong>支持现拍，也支持本地相册</strong>
            </div>
            <label className="field field-compact">
              <span>简单说明（可选）</span>
              <textarea
                rows={3}
                value={dishHint}
                onChange={(event) => setDishHint(event.target.value)}
                placeholder="例如：鸡胸肉沙拉、米饭半碗、少油，或写主要食材"
              />
            </label>
            <div className="capture-card-actions">
              <button
                className="secondary-button"
                type="button"
                onClick={() => dishCameraInputRef.current?.click()}
                disabled={uploadMutation.isPending}
              >
                {uploadMutation.isPending && draftType === "dish_estimate" ? "上传中…" : "拍照识别"}
              </button>
              <button
                className="secondary-button secondary-button-muted"
                type="button"
                onClick={() => dishLibraryInputRef.current?.click()}
                disabled={uploadMutation.isPending}
              >
                相册导入
              </button>
            </div>
          </section>
        </div>
      {draftQuery.data?.status === "ready" ? (
        <div className="summary-grid">
          <article className="summary-item">
            <strong>AI 估算说明</strong>
            <span>{draftQuery.data.raw_text ?? "这次没有返回额外说明。"}</span>
          </article>
          <article className="summary-item">
            <strong>计重口径</strong>
            <span>{weightScopeLabel(draftQuery.data.estimated_scope)}</span>
          </article>
          <article className="summary-item">
            <strong>重量拆分</strong>
            <span>{formatDraftWeightBreakdown(draftQuery.data)}</span>
          </article>
          <article className="summary-item">
            <strong>估算依据</strong>
            <span>{draftQuery.data.portion_basis ?? "这次没有返回额外的份量依据。"}</span>
          </article>
          <article className="summary-item">
            <strong>建议克重</strong>
            <span>
              {draftQuery.data.estimated_grams
                ? `已自动带入 ${draftQuery.data.estimated_grams.toFixed(0)} g，你仍然可以按实际吃掉的重量改掉。`
                : "这次没有返回可靠克重，建议手动填写。"}
            </span>
          </article>
        </div>
      ) : null}
      <p className="panel-muted">支持拍照识别，也支持从相册导入图片。</p>
      </div>

      <form className="panel stack-form" onSubmit={handleSubmit}>
        <div className="panel-header">
          <h2>确认本餐</h2>
          <span>按实际食用量落单</span>
        </div>
        <div className="chips">
          {Object.entries(mealSlotLabels).map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={mealSlot === value ? "chip chip-active" : "chip"}
              onClick={() => setMealSlot(value)}
            >
              {label}
            </button>
          ))}
        </div>

        <label className="field">
          <span>进食时间</span>
          <input type="datetime-local" value={consumedAt} onChange={(event) => setConsumedAt(event.target.value)} required />
        </label>
        <div className="actions actions-inline">
          <button className="secondary-button secondary-button-muted" type="button" onClick={useCurrentTime}>
            写入当前时间
          </button>
        </div>
        <label className="field">
          <span>食物名称</span>
          <input value={foodName} onChange={(event) => setFoodName(event.target.value)} required />
        </label>
        <label className="field">
          <span>实际克重</span>
          <input type="number" step="1" value={actualGrams} onChange={(event) => setActualGrams(event.target.value)} required />
        </label>
        <div className="grid-form">
          <label className="field">
            <span>每 100g 热量</span>
            <input type="number" step="0.1" value={per100Kcal} onChange={(event) => setPer100Kcal(event.target.value)} required />
          </label>
          <label className="field">
            <span>每 100g 碳水</span>
            <input type="number" step="0.1" value={per100Carb} onChange={(event) => setPer100Carb(event.target.value)} />
          </label>
          <label className="field">
            <span>每 100g 脂肪</span>
            <input type="number" step="0.1" value={per100Fat} onChange={(event) => setPer100Fat(event.target.value)} />
          </label>
          <label className="field">
            <span>每 100g 蛋白质</span>
            <input type="number" step="0.1" value={per100Protein} onChange={(event) => setPer100Protein(event.target.value)} />
          </label>
        </div>
        <label className="field">
          <span>每 100g 钠 mg</span>
          <input type="number" step="0.1" value={per100Sodium} onChange={(event) => setPer100Sodium(event.target.value)} />
        </label>
        <p className="status-banner status-info">按当前输入估算，本餐总热量约 {totalKcalPreview} kcal。</p>
        {macroPreview ? (
          <div className="summary-grid">
            <article className="summary-item">
              <strong>碳水占比</strong>
              <span>{macroPreview.carbG.toFixed(1)} g · {macroPreview.carbPct.toFixed(1)}%</span>
            </article>
            <article className="summary-item">
              <strong>蛋白质占比</strong>
              <span>{macroPreview.proteinG.toFixed(1)} g · {macroPreview.proteinPct.toFixed(1)}%</span>
            </article>
            <article className="summary-item">
              <strong>脂肪占比</strong>
              <span>{macroPreview.fatG.toFixed(1)} g · {macroPreview.fatPct.toFixed(1)}%</span>
            </article>
          </div>
        ) : null}
        {notice ? <p className={createMealMutation.isError ? "status-banner status-error" : "status-banner status-success"}>{notice}</p> : null}
        <button className="primary-button" type="submit" disabled={createMealMutation.isPending || uploadMutation.isPending}>
          {createMealMutation.isPending ? "保存中…" : "确认保存餐食"}
        </button>
      </form>

      <section className="panel">
        <div className="panel-header">
          <h2>今日宏量进度</h2>
          <span>{todayReportQuery.data?.report_date ?? today}</span>
        </div>
        {todayMacroStatus && todayMacroTarget ? (
          <div className="summary-grid">
            <article className="summary-item">
              <strong>目标摄入</strong>
              <span>
                {typeof todayPayload?.goal_intake_kcal === "number"
                  ? `${Number(todayPayload.goal_intake_kcal).toFixed(0)} kcal`
                  : "--"}
              </span>
            </article>
            <article className="summary-item">
              <strong>碳水</strong>
              <span>
                {Number(todayMacroStatus.carb?.actual_g ?? 0).toFixed(1)} / {Number(todayMacroTarget.carb_g ?? 0).toFixed(1)} g ·{" "}
                {macroStatusLabel(todayMacroStatus.carb?.status)}
              </span>
            </article>
            <article className="summary-item">
              <strong>蛋白质</strong>
              <span>
                {Number(todayMacroStatus.protein?.actual_g ?? 0).toFixed(1)} / {Number(todayMacroTarget.protein_g ?? 0).toFixed(1)} g ·{" "}
                {macroStatusLabel(todayMacroStatus.protein?.status)}
              </span>
            </article>
            <article className="summary-item">
              <strong>脂肪</strong>
              <span>
                {Number(todayMacroStatus.fat?.actual_g ?? 0).toFixed(1)} / {Number(todayMacroTarget.fat_g ?? 0).toFixed(1)} g ·{" "}
                {macroStatusLabel(todayMacroStatus.fat?.status)}
              </span>
            </article>
          </div>
        ) : (
          <p className="panel-muted">补一条体重并生成今日日报后，这里会显示按最新体重动态计算的 BMR、TDEE 和每日宏量目标。</p>
        )}
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>最近餐食</h2>
          <span>{recentMealsQuery.data?.length ?? 0} 条</span>
        </div>
        <div className="timeline">
          {(recentMealsQuery.data ?? []).slice(0, 12).map((meal) => (
            <button key={meal.id} className="timeline-item timeline-item-button" type="button" onClick={() => applyMeal(meal.id)}>
              <strong>
                {meal.food_name} · {meal.actual_grams}g
              </strong>
              <span>
                {mealSlotLabels[meal.meal_slot] ?? meal.meal_slot} · {meal.kcal.toFixed(0)} kcal · {formatDateTime(meal.consumed_at)}
              </span>
            </button>
          ))}
        </div>
      </section>
    </Screen>
  );
}

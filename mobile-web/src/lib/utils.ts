export function formatDate(value: Date | string): string {
  const target = typeof value === "string" ? new Date(value) : value;
  return target.toISOString().slice(0, 10);
}

export function formatDateTime(value: Date | string): string {
  const target = typeof value === "string" ? new Date(value) : value;
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(target);
}

export function formatDateLabel(value: Date | string): string {
  const target = typeof value === "string" ? new Date(value) : value;
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "short"
  }).format(target);
}

export function toDateInputValue(value: Date | string): string {
  return formatDate(value);
}

export function toDateTimeLocalValue(value: Date | string): string {
  const target = typeof value === "string" ? new Date(value) : value;
  const local = new Date(target.getTime() - target.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

export function currentDateTimeLocalValue(): string {
  return toDateTimeLocalValue(new Date());
}

export function toIsoString(value: string): string {
  return new Date(value).toISOString();
}

export function getTodayDate(): string {
  return toDateInputValue(new Date());
}

export function getCurrentMonth(): string {
  return new Date().toISOString().slice(0, 7);
}

export function getWeekStart(value: Date = new Date()): string {
  const target = new Date(value);
  const day = (target.getDay() + 6) % 7;
  target.setDate(target.getDate() - day);
  target.setHours(0, 0, 0, 0);
  return formatDate(target);
}

export function formatNumber(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(value)) {
    return "--";
  }
  return new Intl.NumberFormat("zh-CN", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits
  }).format(value);
}

export function formatRelativeStatus(value: string | null | undefined): string {
  if (!value) {
    return "未连接";
  }
  return value;
}

export function per100Value(total: number | null | undefined, grams: number | null | undefined): string {
  if (total == null || grams == null || grams <= 0) {
    return "";
  }
  return (total / (grams / 100)).toFixed(1);
}

export function macroPercentages(input: {
  carbG?: number | null;
  fatG?: number | null;
  proteinG?: number | null;
}): { carbPct: number; fatPct: number; proteinPct: number } {
  const carbKcal = (input.carbG ?? 0) * 4;
  const fatKcal = (input.fatG ?? 0) * 9;
  const proteinKcal = (input.proteinG ?? 0) * 4;
  const total = carbKcal + fatKcal + proteinKcal;
  if (total <= 0) {
    return { carbPct: 0, fatPct: 0, proteinPct: 0 };
  }
  return {
    carbPct: Number(((carbKcal / total) * 100).toFixed(1)),
    fatPct: Number(((fatKcal / total) * 100).toFixed(1)),
    proteinPct: Number(((proteinKcal / total) * 100).toFixed(1))
  };
}

export type NutritionTargets = {
  intakeKcal: number;
  carbG: number;
  fatG: number;
  proteinG: number;
  carbPct: number;
  fatPct: number;
  proteinPct: number;
};

export function calculateNutritionTargets(input: {
  weightKg?: number | null;
  tdee?: number | null;
  goalDeficitKcal?: number | null;
}): NutritionTargets | null {
  const weightKg = input.weightKg ?? null;
  const tdee = input.tdee ?? null;
  const goalDeficitKcal = input.goalDeficitKcal ?? 0;
  if (weightKg == null || weightKg <= 0 || tdee == null) {
    return null;
  }

  const intakeKcal = Math.max(tdee - goalDeficitKcal, 0);
  let proteinG = Math.max(weightKg * 1.6, 0);
  let fatG = Math.max(weightKg * 0.8, 0);
  let proteinKcal = proteinG * 4;
  let fatKcal = fatG * 9;
  const minimumMacroKcal = proteinKcal + fatKcal;

  if (minimumMacroKcal > intakeKcal && minimumMacroKcal > 0) {
    const scale = intakeKcal / minimumMacroKcal;
    proteinG *= scale;
    fatG *= scale;
    proteinKcal = proteinG * 4;
    fatKcal = fatG * 9;
  }

  const carbKcal = Math.max(intakeKcal - proteinKcal - fatKcal, 0);
  const carbG = carbKcal / 4;
  const ratios = macroPercentages({ carbG, fatG, proteinG });
  return {
    intakeKcal: Number(intakeKcal.toFixed(1)),
    carbG: Number(carbG.toFixed(1)),
    fatG: Number(fatG.toFixed(1)),
    proteinG: Number(proteinG.toFixed(1)),
    carbPct: ratios.carbPct,
    fatPct: ratios.fatPct,
    proteinPct: ratios.proteinPct
  };
}

export function joinMealSlots(slots: string[]): string {
  const map: Record<string, string> = {
    breakfast: "早餐",
    lunch: "午餐",
    dinner: "晚餐",
    snack: "加餐"
  };
  return slots.map((slot) => map[slot] ?? slot).join(" / ");
}

export function resolveAssetUrl(path: string | null | undefined): string | null {
  if (!path) {
    return null;
  }
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  return new URL(path, window.location.origin).toString();
}

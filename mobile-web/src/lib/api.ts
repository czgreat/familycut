import { z } from "zod";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

const authResponseSchema = z.object({
  member_id: z.string(),
  household_id: z.string(),
  display_name: z.string(),
  role: z.string(),
  tokens: z.object({
    access_token: z.string(),
    refresh_token: z.string(),
    token_type: z.string()
  })
});

const memberProfileSchema = z.object({
  id: z.string(),
  household_id: z.string(),
  username: z.string(),
  display_name: z.string(),
  role: z.string(),
  sex: z.string().nullable(),
  birth_year: z.number().nullable(),
  height_cm: z.number().nullable(),
  activity_factor: z.number(),
  goal_deficit_kcal: z.number(),
  meal_slots: z.array(z.string()),
  unit_preference: z.string(),
  share_by_default: z.boolean()
});

const invitationPreviewSchema = z.object({
  code: z.string(),
  role: z.string()
});

const measurementSchema = z.object({
  id: z.string(),
  source: z.string(),
  measured_at: z.string(),
  weight_kg: z.number(),
  body_fat_pct: z.number().nullable(),
  impedance: z.number().nullable(),
  note: z.string().nullable()
});

const nutritionDraftSchema = z.object({
  id: z.string(),
  draft_type: z.string(),
  status: z.string(),
  food_name: z.string().nullable(),
  hint_text: z.string().nullable().optional(),
  image_path: z.string(),
  image_url: z.string().nullable().optional(),
  raw_text: z.string().nullable(),
  estimated_grams: z.number().nullable().optional(),
  estimated_solid_grams: z.number().nullable().optional(),
  estimated_liquid_grams: z.number().nullable().optional(),
  estimated_scope: z.string().nullable().optional(),
  portion_basis: z.string().nullable().optional(),
  per_100g_kcal: z.number().nullable(),
  per_100g_carb_g: z.number().nullable(),
  per_100g_fat_g: z.number().nullable(),
  per_100g_protein_g: z.number().nullable(),
  per_100g_sodium_mg: z.number().nullable(),
  confidence: z.number().nullable(),
  error_message: z.string().nullable().optional(),
  completed_at: z.string().nullable().optional()
});

const mealSchema = z.object({
  id: z.string(),
  draft_id: z.string().nullable().optional(),
  draft_type: z.string().nullable().optional(),
  meal_slot: z.string(),
  consumed_at: z.string(),
  food_name: z.string(),
  actual_grams: z.number(),
  kcal: z.number(),
  carb_g: z.number(),
  fat_g: z.number(),
  protein_g: z.number(),
  sodium_mg: z.number().nullable(),
  is_shared: z.boolean(),
  source_image_path: z.string().nullable().optional(),
  source_image_url: z.string().nullable().optional(),
  source_food_name: z.string().nullable().optional(),
  source_raw_text: z.string().nullable().optional(),
  source_estimated_grams: z.number().nullable().optional(),
  source_estimated_solid_grams: z.number().nullable().optional(),
  source_estimated_liquid_grams: z.number().nullable().optional(),
  source_estimated_scope: z.string().nullable().optional(),
  source_portion_basis: z.string().nullable().optional(),
  corrections: z.record(z.unknown()).nullable().optional()
});

const dailyReportSchema = z.object({
  id: z.string(),
  report_date: z.string(),
  status: z.string(),
  payload: z.record(z.unknown()),
  image_path: z.string().nullable(),
  image_url: z.string().nullable().optional(),
  is_shared: z.boolean()
});

const periodicReportSchema = z.object({
  report_type: z.string(),
  period_start: z.string(),
  period_end: z.string(),
  status: z.string(),
  payload: z.record(z.unknown()),
  image_path: z.string().nullable(),
  image_url: z.string().nullable().optional()
});

export type AuthResponse = z.infer<typeof authResponseSchema>;
export type MemberProfile = z.infer<typeof memberProfileSchema>;
export type InvitationPreview = z.infer<typeof invitationPreviewSchema>;
export type MeasurementEntry = z.infer<typeof measurementSchema>;
export type NutritionDraft = z.infer<typeof nutritionDraftSchema>;
export type MealEntry = z.infer<typeof mealSchema>;
export type DailyReport = z.infer<typeof dailyReportSchema>;
export type PeriodicReport = z.infer<typeof periodicReportSchema>;

export type MemberProfileUpdate = Partial<{
  display_name: string;
  sex: string | null;
  birth_year: number | null;
  height_cm: number | null;
  activity_factor: number | null;
  goal_deficit_kcal: number | null;
  meal_slots: string[] | null;
  unit_preference: string | null;
  share_by_default: boolean | null;
}>;

export type MeasurementInput = {
  measured_at: string;
  weight_kg: number;
  body_fat_pct?: number;
  note?: string;
};

export type MealInput = {
  draft_id?: string;
  meal_slot: string;
  consumed_at: string;
  food_name: string;
  actual_grams: number;
  kcal: number;
  carb_g: number;
  fat_g: number;
  protein_g: number;
  sodium_mg?: number;
  corrections?: Record<string, unknown>;
};

function buildUrl(path: string, params?: Record<string, string | number | undefined>): string {
  const base = API_BASE.startsWith("http") ? new URL(API_BASE) : new URL(API_BASE, window.location.origin);
  const url = new URL(path.replace(/^\//, ""), `${base.toString().replace(/\/$/, "")}/`);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== "") {
        url.searchParams.set(key, String(value));
      }
    });
  }
  if (API_BASE.startsWith("http")) {
    return url.toString();
  }
  return `${base.pathname.replace(/\/$/, "")}${url.pathname.replace(base.pathname.replace(/\/$/, ""), "")}${url.search}`;
}

async function readErrorMessage(response: Response): Promise<string> {
  const text = await response.text();
  if (!text) {
    return `请求失败：${response.status}`;
  }
  try {
    const parsed = JSON.parse(text) as { detail?: string };
    return parsed.detail ?? text;
  } catch {
    return text;
  }
}

async function requestJson<T>(
  path: string,
  schema: z.ZodType<T>,
  init?: RequestInit,
  params?: Record<string, string | number | undefined>
): Promise<T> {
  const response = await fetch(buildUrl(path, params), init);
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
  const json = (await response.json()) as unknown;
  return schema.parse(json);
}

function buildAuthHeaders(token?: string, extra?: HeadersInit): Headers {
  const headers = new Headers(extra);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  return headers;
}

export async function loginMember(username: string, password: string): Promise<AuthResponse> {
  return requestJson(
    "/auth/login",
    authResponseSchema,
    {
      method: "POST",
      headers: buildAuthHeaders(undefined, { "Content-Type": "application/json" }),
      body: JSON.stringify({ username, password })
    }
  );
}

export async function previewInvite(code: string): Promise<InvitationPreview> {
  return requestJson(`/auth/invite-preview/${code}`, invitationPreviewSchema);
}

export async function registerByInvite(payload: {
  code: string;
  username: string;
  password: string;
  display_name: string;
  sex: string;
  birth_year: number;
}): Promise<AuthResponse> {
  return requestJson(
    "/auth/register-by-invite",
    authResponseSchema,
    {
      method: "POST",
      headers: buildAuthHeaders(undefined, { "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    }
  );
}

export async function fetchCurrentMember(token: string): Promise<MemberProfile> {
  return requestJson("/members/me", memberProfileSchema, {
    headers: buildAuthHeaders(token)
  });
}

export async function updateCurrentMember(token: string, payload: MemberProfileUpdate): Promise<MemberProfile> {
  return requestJson(
    "/members/me",
    memberProfileSchema,
    {
      method: "PUT",
      headers: buildAuthHeaders(token, { "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    }
  );
}

export async function listMeasurements(token: string): Promise<MeasurementEntry[]> {
  return requestJson("/measurements", z.array(measurementSchema), {
    headers: buildAuthHeaders(token)
  });
}

export async function createMeasurement(token: string, payload: MeasurementInput): Promise<MeasurementEntry> {
  return requestJson(
    "/measurements",
    measurementSchema,
    {
      method: "POST",
      headers: buildAuthHeaders(token, { "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    }
  );
}

export async function listMeals(token: string, targetDate?: string): Promise<MealEntry[]> {
  return requestJson(
    "/meals",
    z.array(mealSchema),
    {
      headers: buildAuthHeaders(token)
    },
    { target_date: targetDate }
  );
}

export async function createMeal(token: string, payload: MealInput): Promise<MealEntry> {
  return requestJson(
    "/meals",
    mealSchema,
    {
      method: "POST",
      headers: buildAuthHeaders(token, { "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    }
  );
}

export async function createNutritionDraft(
  token: string,
  image: File,
  draftType: "label" | "dish_estimate",
  hintText?: string
): Promise<NutritionDraft> {
  const formData = new FormData();
  formData.append("draft_type", draftType);
  if (hintText?.trim()) {
    formData.append("hint_text", hintText.trim());
  }
  formData.append("image", image, image.name);
  return requestJson("/nutrition/drafts", nutritionDraftSchema, {
    method: "POST",
    headers: buildAuthHeaders(token),
    body: formData
  });
}

export async function getNutritionDraft(token: string, draftId: string): Promise<NutritionDraft> {
  return requestJson(`/nutrition/drafts/${draftId}`, nutritionDraftSchema, {
    headers: buildAuthHeaders(token)
  });
}

export async function fetchRecentReports(token: string, limit = 7): Promise<DailyReport[]> {
  return requestJson(
    "/reports/recent",
    z.array(dailyReportSchema),
    {
      headers: buildAuthHeaders(token)
    },
    { limit }
  );
}

export async function fetchDailyReport(token: string, reportDate: string): Promise<DailyReport> {
  return requestJson(`/reports/daily/${reportDate}`, dailyReportSchema, {
    headers: buildAuthHeaders(token)
  });
}

export async function fetchWeeklyReport(token: string, startDate: string): Promise<PeriodicReport> {
  return requestJson(`/reports/weekly/${startDate}`, periodicReportSchema, {
    headers: buildAuthHeaders(token)
  });
}

export async function fetchMonthlyReport(token: string, yearMonth: string): Promise<PeriodicReport> {
  return requestJson(`/reports/monthly/${yearMonth}`, periodicReportSchema, {
    headers: buildAuthHeaders(token)
  });
}

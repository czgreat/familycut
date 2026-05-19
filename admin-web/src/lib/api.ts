export type DashboardSummary = {
  member_count: number;
  measurement_count: number;
  meal_count: number;
  shared_media_count: number;
};

export type AuthResponse = {
  member_id: string;
  household_id: string;
  display_name: string;
  role: string;
  tokens: {
    access_token: string;
    refresh_token: string;
    token_type: string;
  };
};

export type MemberProfile = {
  id: string;
  household_id: string;
  username: string;
  display_name: string;
  role: string;
  sex: string | null;
  birthdate: string | null;
  height_cm: number | null;
  activity_factor: number;
  goal_deficit_kcal: number;
  meal_slots: string[];
  unit_preference: string;
  share_by_default: boolean;
};

export type MemberSummary = {
  id: string;
  username: string;
  display_name: string;
  role: string;
  height_cm: number | null;
  activity_factor: number;
  goal_deficit_kcal: number;
  meal_slots: string[];
  share_by_default: boolean;
  measurement_count: number;
  meal_count: number;
  report_count: number;
  latest_weight_kg: number | null;
  latest_body_fat_pct: number | null;
  latest_measured_at: string | null;
  latest_report_date: string | null;
};

export type MeasurementHistoryItem = {
  measured_at: string;
  weight_kg: number;
  body_fat_pct: number | null;
};

export type MealHistoryItem = {
  consumed_at: string;
  meal_slot: string;
  food_name: string;
  actual_grams: number;
  kcal: number;
};

export type ExerciseHistoryItem = {
  occurred_at: string;
  exercise_type: string;
  distance_km: number | null;
  duration_min: number | null;
  estimated_kcal: number | null;
  note: string | null;
};

export type ReportHistoryItem = {
  report_date: string;
  deficit_kcal: number | null;
  deficit_hit: boolean | null;
  carb_g: number | null;
  fat_g: number | null;
  protein_g: number | null;
};

export type MemberDetail = MemberSummary & {
  recent_measurements: MeasurementHistoryItem[];
  recent_meals: MealHistoryItem[];
  recent_exercises: ExerciseHistoryItem[];
  recent_reports: ReportHistoryItem[];
};

export type InvitationResponse = {
  code: string;
  role: string;
};

export type InvitationHistoryItem = {
  id: string;
  code: string;
  role: string;
  created_at: string;
  used_at: string | null;
  used_by_member_id: string | null;
};

export type AppSettings = {
  ai_enabled: boolean;
  ai_base_url: string;
  ai_api_key: string;
  ai_model_name: string;
  ai_timeout_sec: number;
  ai_proxy_enabled: boolean;
  ai_proxy_url: string | null;
  report_generate_hour: number;
  report_push_hour: number;
  generic_webhook_enabled: boolean;
  generic_webhook_url: string;
  wechatbot_webhook_enabled: boolean;
  wechatbot_base_url: string;
  wechatbot_token: string;
  wechatbot_target: string;
  wechatbot_is_room: boolean;
};

export type AiConnectionTestResult = {
  ok: boolean;
  transport: string;
  model_name: string;
  detail: string;
  status_code: number | null;
};

export type DailyReportSummary = {
  id: string;
  report_date: string;
  status: string;
  payload: Record<string, unknown>;
  image_path: string | null;
  image_url: string | null;
  is_shared: boolean;
};

export type MediaAsset = {
  id: string;
  media_type: string;
  captured_at: string;
  original_path: string;
  preview_path: string | null;
  original_url: string | null;
  preview_url: string | null;
  is_shared: boolean;
  note: string | null;
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function loginAdmin(username: string, password: string): Promise<AuthResponse> {
  const payload = await requestJson<AuthResponse>("/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ username, password })
  });

  if (payload.role !== "admin") {
    throw new Error("只有管理员可以登录后台。");
  }

  return payload;
}

export async function fetchCurrentMember(token: string): Promise<MemberProfile> {
  return requestJson<MemberProfile>("/members/me", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export async function fetchDashboard(token: string): Promise<DashboardSummary> {
  return requestJson<DashboardSummary>("/reports/dashboard", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export async function fetchRecentHouseholdReports(token: string): Promise<DailyReportSummary[]> {
  return requestJson<DailyReportSummary[]>("/reports/history", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export async function fetchHouseholdSelfies(token: string): Promise<MediaAsset[]> {
  return requestJson<MediaAsset[]>("/media/household/selfies", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export async function fetchMemberSummaries(token: string): Promise<MemberSummary[]> {
  return requestJson<MemberSummary[]>("/members/summary", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export async function fetchMemberDetail(token: string, memberId: string): Promise<MemberDetail> {
  return requestJson<MemberDetail>(`/members/${memberId}/detail`, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export async function fetchInvitationHistory(token: string): Promise<InvitationHistoryItem[]> {
  return requestJson<InvitationHistoryItem[]>("/members/invitations", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export async function createMemberInvitation(token: string): Promise<InvitationResponse> {
  return requestJson<InvitationResponse>("/members/invitations", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({ role: "member" })
  });
}

export async function fetchAppSettings(token: string): Promise<AppSettings> {
  return requestJson<AppSettings>("/settings/app-config", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export async function saveAppSettings(token: string, payload: AppSettings): Promise<AppSettings> {
  return requestJson<AppSettings>("/settings/app-config", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify(payload)
  });
}

export async function testAiConnection(token: string, payload: Pick<AppSettings, "ai_base_url" | "ai_api_key" | "ai_model_name" | "ai_timeout_sec" | "ai_proxy_enabled" | "ai_proxy_url">): Promise<AiConnectionTestResult> {
  return requestJson<AiConnectionTestResult>("/settings/tests/ai-connection", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify(payload)
  });
}

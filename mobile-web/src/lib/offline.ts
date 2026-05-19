type StoredRecord<T> = {
  updatedAt: string;
  value: T;
};

type HomeSnapshot = {
  latestWeightKg: number | null;
  latestBodyFatPct: number | null;
  mealsToday: number;
  totalKcalToday: number;
  latestReportDate: string | null;
  latestDeficitKcal: number | null;
};

type WeightDraft = {
  measuredAt: string;
  weightKg: string;
  bodyFatPct: string;
  note: string;
};

type MealDraft = {
  mealSlot: string;
  consumedAt: string;
  foodName: string;
  actualGrams: string;
  per100Kcal: string;
  per100Carb: string;
  per100Fat: string;
  per100Protein: string;
  per100Sodium: string;
  draftId: string;
  dishHint: string;
};

type PendingNutritionDraft = {
  draftId: string;
  draftType: string;
};

const DB_NAME = "familycut-mobile-web";
const STORE_NAME = "cache";
const FALLBACK_PREFIX = "familycut-mobile:";

const KEYS = {
  home: "home_snapshot",
  weightDraft: "weight_draft",
  mealDraft: "meal_draft",
  pendingNutritionDraft: "pending_nutrition_draft"
} as const;

function supportsIndexedDb(): boolean {
  return typeof window !== "undefined" && "indexedDB" in window;
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = window.indexedDB.open(DB_NAME, 1);
    request.onerror = () => reject(request.error ?? new Error("无法打开本地缓存数据库。"));
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
    };
    request.onsuccess = () => resolve(request.result);
  });
}

async function readValue<T>(key: string): Promise<T | null> {
  if (!supportsIndexedDb()) {
    const raw = window.localStorage.getItem(`${FALLBACK_PREFIX}${key}`);
    if (!raw) {
      return null;
    }
    return JSON.parse(raw) as StoredRecord<T>["value"];
  }

  const db = await openDb();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, "readonly");
    const request = transaction.objectStore(STORE_NAME).get(key);
    request.onerror = () => reject(request.error ?? new Error("读取本地缓存失败。"));
    request.onsuccess = () => {
      const record = request.result as StoredRecord<T> | undefined;
      resolve(record?.value ?? null);
    };
  });
}

async function writeValue<T>(key: string, value: T): Promise<void> {
  const record: StoredRecord<T> = {
    updatedAt: new Date().toISOString(),
    value
  };

  if (!supportsIndexedDb()) {
    window.localStorage.setItem(`${FALLBACK_PREFIX}${key}`, JSON.stringify(record));
    return;
  }

  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, "readwrite");
    const request = transaction.objectStore(STORE_NAME).put(record, key);
    request.onerror = () => reject(request.error ?? new Error("写入本地缓存失败。"));
    request.onsuccess = () => resolve();
  });
}

async function removeValue(key: string): Promise<void> {
  if (!supportsIndexedDb()) {
    window.localStorage.removeItem(`${FALLBACK_PREFIX}${key}`);
    return;
  }

  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, "readwrite");
    const request = transaction.objectStore(STORE_NAME).delete(key);
    request.onerror = () => reject(request.error ?? new Error("删除本地缓存失败。"));
    request.onsuccess = () => resolve();
  });
}

export async function loadHomeSnapshot(): Promise<HomeSnapshot | null> {
  return readValue<HomeSnapshot>(KEYS.home);
}

export async function saveHomeSnapshot(value: HomeSnapshot): Promise<void> {
  await writeValue(KEYS.home, value);
}

export async function loadWeightDraft(): Promise<WeightDraft | null> {
  return readValue<WeightDraft>(KEYS.weightDraft);
}

export async function saveWeightDraft(value: WeightDraft): Promise<void> {
  await writeValue(KEYS.weightDraft, value);
}

export async function clearWeightDraft(): Promise<void> {
  await removeValue(KEYS.weightDraft);
}

export async function loadMealDraft(): Promise<MealDraft | null> {
  return readValue<MealDraft>(KEYS.mealDraft);
}

export async function saveMealDraft(value: MealDraft): Promise<void> {
  await writeValue(KEYS.mealDraft, value);
}

export async function clearMealDraft(): Promise<void> {
  await removeValue(KEYS.mealDraft);
}

export async function loadPendingNutritionDraft(): Promise<PendingNutritionDraft | null> {
  return readValue<PendingNutritionDraft>(KEYS.pendingNutritionDraft);
}

export async function savePendingNutritionDraft(value: PendingNutritionDraft): Promise<void> {
  await writeValue(KEYS.pendingNutritionDraft, value);
}

export async function clearPendingNutritionDraft(): Promise<void> {
  await removeValue(KEYS.pendingNutritionDraft);
}

export async function clearOfflineData(): Promise<void> {
  await Promise.all([
    removeValue(KEYS.home),
    removeValue(KEYS.weightDraft),
    removeValue(KEYS.mealDraft),
    removeValue(KEYS.pendingNutritionDraft)
  ]);

  if ("caches" in window) {
    const names = await window.caches.keys();
    await Promise.all(names.filter((name) => name.startsWith("familycut-")).map((name) => window.caches.delete(name)));
  }
}

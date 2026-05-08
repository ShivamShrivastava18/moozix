import type {
  AuthStatus,
  CompatibilityResult,
  TasteProfile,
  UserPublic,
} from "./types";

/**
 * In dev, Vite proxies /api/* to the FastAPI server (see vite.config.ts).
 * In prod, set VITE_API_BASE to the deployed backend.
 */
const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
    ...init,
  });

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  let body: unknown = undefined;
  try {
    body = text ? JSON.parse(text) : undefined;
  } catch {
    body = text;
  }

  if (!res.ok) {
    const detail =
      (body as { detail?: string })?.detail ??
      (typeof body === "string" ? body : `HTTP ${res.status}`);
    throw new ApiError(res.status, detail);
  }

  return body as T;
}

// ---------- Auth ----------
export const auth = {
  loginUrl: () => `${BASE}/auth/login`,
  status: () => request<AuthStatus>("/auth/status"),
  logout: () => request<{ ok: boolean }>("/auth/logout", { method: "POST" }),
};

// ---------- Profile ----------
export const profile = {
  me: (refresh = false) =>
    request<TasteProfile>(`/profile/me${refresh ? "?refresh=true" : ""}`),
  refresh: () =>
    request<TasteProfile>("/profile/me/refresh", { method: "POST" }),
  get: (userId: string) =>
    request<TasteProfile>(`/profile/${encodeURIComponent(userId)}`),
  list: () => request<UserPublic[]>("/profile"),
};

// ---------- Compare ----------
export const compare = {
  run: (params: {
    user_b: string;
    user_a?: string;
    include_llm?: boolean;
    force?: boolean;
  }) =>
    request<CompatibilityResult>("/compare", {
      method: "POST",
      body: JSON.stringify({ include_llm: true, force: false, ...params }),
    }),
  cached: (a: string, b: string) =>
    request<CompatibilityResult>(
      `/compare/${encodeURIComponent(a)}/${encodeURIComponent(b)}`,
    ),
};

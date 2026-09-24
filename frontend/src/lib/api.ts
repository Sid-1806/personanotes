import axios, { AxiosError } from "axios";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

export const TOKEN_KEY = "token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string) {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* private mode / blocked storage — the session just won't persist */
  }
}

export function clearToken() {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}

/**
 * Broadcast that the session expired instead of navigating away.
 *
 * A hard `window.location.href = '/login'` threw away whatever the user had in
 * the editor. The app listens for this and shows a re-auth modal over the top,
 * so unsaved work survives signing back in.
 */
export const SESSION_EXPIRED_EVENT = "personanotes:session-expired";

function announceSessionExpired() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT));
}

export type ApiErrorKind =
  | "network"
  | "unauthorized"
  | "rate_limited"
  | "validation"
  | "not_found"
  | "conflict"
  | "unavailable"
  | "server"
  | "unknown";

/** A failure the UI can respond to specifically, rather than "please try again". */
export class ApiError extends Error {
  kind: ApiErrorKind;
  status: number | null;
  retryAfter: number | null;

  constructor(
    message: string,
    kind: ApiErrorKind,
    status: number | null = null,
    retryAfter: number | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

function classify(error: AxiosError): ApiError {
  if (!error.response) {
    return new ApiError(
      "Couldn't reach PersonaNotes. Check your connection and try again.",
      "network",
    );
  }

  const { status, data, headers } = error.response;
  const detail =
    (data as { detail?: string } | undefined)?.detail ??
    "Something went wrong. Please try again.";

  switch (status) {
    case 401:
      return new ApiError("Your session expired.", "unauthorized", status);
    case 403:
      return new ApiError(detail, "unauthorized", status);
    case 404:
      return new ApiError(detail, "not_found", status);
    case 409:
      return new ApiError(detail, "conflict", status);
    case 422:
      return new ApiError(detail, "validation", status);
    case 429: {
      const header = headers?.["retry-after"];
      const retryAfter = header ? Number(header) : null;
      return new ApiError(
        detail,
        "rate_limited",
        status,
        Number.isFinite(retryAfter) ? retryAfter : 60,
      );
    }
    case 503:
      return new ApiError(detail, "unavailable", status);
    default:
      if (status >= 500) return new ApiError(detail, "server", status);
      if (status >= 400) return new ApiError(detail, "validation", status);
      return new ApiError(detail, "unknown", status);
  }
}

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const apiError = classify(error);
    if (apiError.kind === "unauthorized" && error.response?.status === 401) {
      clearToken();
      announceSessionExpired();
    }
    return Promise.reject(apiError);
  },
);

/** Human-readable message for any thrown value. */
export function errorMessage(error: unknown, fallback = "Something went wrong."): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

export function errorKind(error: unknown): ApiErrorKind {
  return error instanceof ApiError ? error.kind : "unknown";
}

export default api;

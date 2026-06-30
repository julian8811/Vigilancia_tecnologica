/**
 * Thin fetch wrapper with cookie-based auth + CSRF double-submit.
 *
 * Tokens live in httpOnly cookies (`vg_access`, `vg_refresh`) that
 * the browser sends automatically. The CSRF double-submit token
 * lives in a JS-readable `vg_csrf` cookie; the SPA reads it via
 * `document.cookie` and echoes the value in the `X-CSRF-Token`
 * header on every mutating request.
 */

import { toast } from "sonner";

// Use relative URLs so Next.js rewrites (next.config.js) proxy /api/*
// to the real backend. This keeps requests same-origin: no CORS preflight,
// no cross-site cookie issues (SameSite=Lax works), and the CSRF cookie
// is always readable via document.cookie on the same domain.
const BASE_URL = "";

/** Name of the CSRF double-submit cookie. Must match the API. */
const CSRF_COOKIE_NAME = "vg_csrf";
/** Name of the header that echoes the CSRF token. Must match the API. */
const CSRF_HEADER = "X-CSRF-Token";
/** Methods that mutate server state and therefore need a CSRF header. */
const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

interface ApiOptions extends Omit<RequestInit, "headers" | "body"> {
  headers?: Record<string, string>;
  body?: unknown;
}

interface ApiErrorBody {
  detail?: string;
  error?: string;
}

export class ApiClientError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiClientError";
    this.status = status;
    this.detail = detail;
  }
}

/** Callback invoked when any API call returns 401. */
let onUnauthorized: (() => void) | null = null;

/**
 * Register a handler to run whenever the API returns 401.
 * The handler should be idempotent and must not throw.
 */
export function setOnUnauthorized(handler: (() => void) | null) {
  onUnauthorized = handler;
}

/**
 * Read the current CSRF token from `document.cookie`.
 *
 * Returns `null` if the cookie is not set yet (e.g. before the
 * first /auth/login response has been received). The server is
 * the source of truth; the SPA only needs a best-effort guess.
 */
export function getCsrfToken(): string | null {
  if (typeof document === "undefined") return null;
  const target = `${CSRF_COOKIE_NAME}=`;
  for (const part of document.cookie.split(";")) {
    const trimmed = part.trim();
    if (trimmed.startsWith(target)) {
      return decodeURIComponent(trimmed.slice(target.length));
    }
  }
  return null;
}

function readErrorDetail(body: ApiErrorBody, fallback: string): string {
  return body.detail || body.error || fallback;
}

async function request<T>(
  endpoint: string,
  options: ApiOptions = {},
): Promise<T> {
  const { headers: extraHeaders, body, ...fetchOptions } = options;

  const headers: Record<string, string> = {
    ...extraHeaders,
  };
  if (!headers["Content-Type"] && body !== undefined && typeof body !== "string") {
    headers["Content-Type"] = "application/json";
  }

  // Attach the CSRF token to every mutating request. The server
  // exempts the bootstrap auth endpoints (login/register/refresh)
  // and rejects other mutations with 403 if the header is missing
  // or doesn't match the cookie.
  const method = (fetchOptions.method ?? "GET").toUpperCase();
  if (MUTATING_METHODS.has(method) && !headers[CSRF_HEADER]) {
    const token = getCsrfToken();
    if (token) {
      headers[CSRF_HEADER] = token;
    } else {
      // The server is the source of truth — it'll return a 403 with
      // a clear error. We log so developers spot the misconfig fast.
      // eslint-disable-next-line no-console
      console.warn(
        "CSRF token not available; mutating request may fail",
      );
    }
  }

  const fetchBody =
    body !== undefined
      ? typeof body === "string"
        ? body
        : JSON.stringify(body)
      : undefined;

  const response = await fetch(`${BASE_URL}/api/v1${endpoint}`, {
    ...fetchOptions,
    method,
    headers,
    body: fetchBody,
    credentials: "include",
  });

  if (!response.ok) {
    const errBody = (await response.json().catch(() => ({}))) as ApiErrorBody;
    const detail = readErrorDetail(errBody, `Error ${response.status}`);

    if (response.status === 401 && onUnauthorized) {
      try {
        onUnauthorized();
      } catch (e) {
        // eslint-disable-next-line no-console
        console.error("onUnauthorized handler threw", e);
      }
    }

    throw new ApiClientError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  get<T>(endpoint: string, options?: ApiOptions) {
    return request<T>(endpoint, { ...options, method: "GET" });
  },
  post<T>(endpoint: string, body?: unknown, options?: ApiOptions) {
    return request<T>(endpoint, { ...options, method: "POST", body });
  },
  put<T>(endpoint: string, body?: unknown, options?: ApiOptions) {
    return request<T>(endpoint, { ...options, method: "PUT", body });
  },
  delete<T>(endpoint: string, options?: ApiOptions) {
    return request<T>(endpoint, { ...options, method: "DELETE" });
  },
  async getRaw(endpoint: string, options?: ApiOptions): Promise<Response> {
    const { headers: extraHeaders, body: _body, ...fetchOptions } = options || {};
    const headers: Record<string, string> = { ...extraHeaders };
    const response = await fetch(`${BASE_URL}/api/v1${endpoint}`, {
      ...fetchOptions,
      method: "GET",
      headers,
      credentials: "include",
    } as RequestInit);
    if (!response.ok) {
      const errBody = (await response.json().catch(() => ({}))) as ApiErrorBody;
      const detail = readErrorDetail(errBody, `Error ${response.status}`);
      if (response.status === 401 && onUnauthorized) {
        try {
          onUnauthorized();
        } catch (e) {
          // eslint-disable-next-line no-console
          console.error("onUnauthorized handler threw", e);
        }
      }
      throw new ApiClientError(response.status, detail);
    }
    return response;
  },
};

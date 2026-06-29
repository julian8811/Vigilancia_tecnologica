/**
 * Thin fetch wrapper with built-in auth token handling.
 *
 * Provides typed fetch interface for the API with automatic
 * auth token injection, consistent error envelope handling, and a
 * 401-interceptor hook so expired tokens trigger a clean logout
 * rather than a silent failure.
 */

import { toast } from "sonner";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ApiOptions extends Omit<RequestInit, "headers" | "body"> {
  headers?: Record<string, string>;
  token?: string;
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

let defaultToken: string | null = null;

/** Callback invoked when any API call returns 401. */
let onUnauthorized: (() => void) | null = null;

export function setAuthToken(token: string | null) {
  defaultToken = token;
}

export function getAuthToken(): string | null {
  return defaultToken;
}

/**
 * Register a handler to run whenever the API returns 401.
 *
 * The auth provider registers this on mount and uses it to clear
 * local state and redirect to /login. The handler should be
 * idempotent (called at most once per session in practice) and
 * must not throw — it is invoked from inside the request() promise
 * chain.
 */
export function setOnUnauthorized(handler: (() => void) | null) {
  onUnauthorized = handler;
}

function readErrorDetail(body: ApiErrorBody, fallback: string): string {
  // API uses {detail: "..."} (audit fix S14); keep {error: "..."} as
  // a defensive fallback for any older endpoint that hasn't been
  // migrated yet.
  return body.detail || body.error || fallback;
}

async function request<T>(
  endpoint: string,
  options: ApiOptions = {},
): Promise<T> {
  const { token: explicitToken, headers: extraHeaders, body, ...fetchOptions } = options;
  const token = explicitToken || defaultToken;

  const headers: Record<string, string> = {
    ...extraHeaders,
  };

  // Only set default Content-Type if not already set (e.g. for form data)
  if (!headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Pass string bodies directly (for URLSearchParams etc.), JSON-stringify objects
  const fetchBody =
    body !== undefined
      ? typeof body === "string"
        ? body
        : JSON.stringify(body)
      : undefined;

  const response = await fetch(`${BASE_URL}/api/v1${endpoint}`, {
    ...fetchOptions,
    headers,
    body: fetchBody,
  });

  if (!response.ok) {
    const errBody = (await response.json().catch(() => ({}))) as ApiErrorBody;
    const detail = readErrorDetail(errBody, `Error ${response.status}`);

    if (response.status === 401 && onUnauthorized) {
      // Fire and forget — we still want to surface the original error
      // to the caller, but the global handler will log the user out
      // and redirect.
      try {
        onUnauthorized();
      } catch (e) {
        toast.error("Tu sesión expiró. Volvé a iniciar sesión.");
      }
    }

    throw new ApiClientError(response.status, detail);
  }

  return response.json() as Promise<T>;
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
  /** Fetch raw response (blob, HTML, etc.) without JSON parsing. */
  async getRaw(endpoint: string, options?: ApiOptions): Promise<Response> {
    const { token: explicitToken, headers: extraHeaders, body: _body, ...fetchOptions } = options || {};
    const token = explicitToken || defaultToken;
    const headers: Record<string, string> = { ...extraHeaders };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    const response = await fetch(`${BASE_URL}/api/v1${endpoint}`, {
      ...fetchOptions,
      method: "GET",
      headers,
    } as RequestInit);
    if (!response.ok) {
      const errBody = (await response.json().catch(() => ({}))) as ApiErrorBody;
      const detail = readErrorDetail(errBody, `Error ${response.status}`);
      if (response.status === 401 && onUnauthorized) {
        try {
          onUnauthorized();
        } catch (e) {
          toast.error("Tu sesión expiró. Volvé a iniciar sesión.");
        }
      }
      throw new ApiClientError(response.status, detail);
    }
    return response;
  },
};

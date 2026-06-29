/**
 * Thin fetch wrapper with cookie-based auth.
 *
 * Tokens live in httpOnly cookies (`vg_access`, `vg_refresh`) that
 * the browser sends automatically. The client never reads or
 * stores them.
 */

import { toast } from "sonner";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

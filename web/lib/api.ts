/**
 * Thin fetch wrapper with built-in auth token handling.
 *
 * Provides typed fetch interface for the API with automatic
 * auth token injection and form-data support.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ApiOptions extends Omit<RequestInit, "headers" | "body"> {
  headers?: Record<string, string>;
  token?: string;
  body?: unknown;
}

interface ApiError {
  error: string;
  status: number;
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

export function setAuthToken(token: string | null) {
  defaultToken = token;
}

export function getAuthToken(): string | null {
  return defaultToken;
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
    const body = (await response.json().catch(() => ({
      error: "Unknown error",
    }))) as ApiError;
    throw new ApiClientError(response.status, body.error);
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
      const body = await response.json().catch(() => ({ error: "Unknown error" }));
      throw new ApiClientError(response.status, body.error || body.detail || "Request failed");
    }
    return response;
  },
};

import { describe, it, expect, vi, beforeEach } from "vitest";
import { api, setAuthToken, getAuthToken, ApiClientError } from "@/lib/api";

beforeEach(() => {
  vi.restoreAllMocks();
  setAuthToken(null);
});

describe("setAuthToken / getAuthToken", () => {
  it("stores and retrieves the token", () => {
    setAuthToken("my-token");
    expect(getAuthToken()).toBe("my-token");
  });

  it("clears token when set to null", () => {
    setAuthToken("old");
    setAuthToken(null);
    expect(getAuthToken()).toBeNull();
  });
});

describe("api.get", () => {
  it("sends a GET request with correct URL", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: "ok" }),
    });
    vi.stubGlobal("fetch", mockFetch);

    const result = await api.get("/projects");
    expect(result).toEqual({ data: "ok" });
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/projects",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("includes auth token when set", async () => {
    setAuthToken("secret");
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({}),
    });
    vi.stubGlobal("fetch", mockFetch);

    await api.get("/projects");
    const headers = mockFetch.mock.calls[0][1].headers;
    expect(headers["Authorization"]).toBe("Bearer secret");
  });

  it("throws ApiClientError on non-ok response", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ error: "Not found" }),
    });
    vi.stubGlobal("fetch", mockFetch);

    await expect(api.get("/missing")).rejects.toThrow(ApiClientError);
    await expect(api.get("/missing")).rejects.toThrow("Not found");
  });
});

describe("api.post", () => {
  it("sends a POST request with JSON body", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 1 }),
    });
    vi.stubGlobal("fetch", mockFetch);

    const result = await api.post("/projects", { name: "Test" });
    expect(result).toEqual({ id: 1 });
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/projects",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ name: "Test" }),
      }),
    );
  });
});

describe("api.getRaw", () => {
  it("returns raw response without JSON parsing", async () => {
    const mockResponse = {
      ok: true,
      blob: () => Promise.resolve(new Blob()),
    };
    const mockFetch = vi.fn().mockResolvedValue(mockResponse);
    vi.stubGlobal("fetch", mockFetch);

    const result = await api.getRaw("/graph/p1/download-json?run_id=r1");
    expect(result).toBe(mockResponse);
  });

  it("throws on non-ok raw response", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      json: () => Promise.resolve({ error: "Forbidden" }),
    });
    vi.stubGlobal("fetch", mockFetch);

    await expect(api.getRaw("/secret")).rejects.toThrow(ApiClientError);
  });
});

describe("api.delete", () => {
  it("sends a DELETE request", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({}),
    });
    vi.stubGlobal("fetch", mockFetch);

    await api.delete("/projects/123");
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/projects/123",
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});

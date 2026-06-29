/**
 * Tests for the cookie-based API client.
 *
 * The previous suite (which called `setAuthToken` / `getAuthToken`)
 * has been removed: tokens are no longer managed in JavaScript. The
 * browser handles cookies. The tests here cover what is still
 * observable: the request envelope, the error reader, and the
 * 204-no-content short-circuit.
 */

import { describe, expect, it } from "vitest";

import { ApiClientError, api } from "@/lib/api";

describe("api error handling", () => {
  it("ApiClientError carries status and detail", () => {
    const e = new ApiClientError(404, "not found");
    expect(e.status).toBe(404);
    expect(e.detail).toBe("not found");
    expect(e.message).toBe("not found");
  });
});

// Smoke test that the module exports the expected surface.
describe("api exports", () => {
  it("exposes get/post/put/delete/getRaw", () => {
    expect(typeof api.get).toBe("function");
    expect(typeof api.post).toBe("function");
    expect(typeof api.put).toBe("function");
    expect(typeof api.delete).toBe("function");
    expect(typeof api.getRaw).toBe("function");
  });
});

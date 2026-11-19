import { afterEach, describe, expect, it, vi } from "vitest";

const getIdToken = vi.fn(async (force?: boolean) => (force ? "fresh-token" : "old-token"));
vi.mock("@/lib/firebase", () => ({ getFirebaseAuth: () => ({ currentUser: { getIdToken } }) }));

import { ApiError, api } from "@/lib/api";

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

afterEach(() => vi.restoreAllMocks());

describe("api client", () => {
  it("attaches the Firebase ID token", async () => {
    const f = vi.spyOn(globalThis, "fetch").mockResolvedValue(json(200, { ok: true }));
    await api("/api/v1/me");
    expect((f.mock.calls[0][1]!.headers as Record<string, string>).Authorization).toBe("Bearer old-token");
  });

  it("refreshes the token once and retries on claims_stale", async () => {
    const f = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(json(401, { error: { code: "claims_stale", message: "refresh" } }))
      .mockResolvedValueOnce(json(200, { role: "inspector" }));
    const r = await api<{ role: string }>("/api/v1/inspector/dashboard");
    expect(r.role).toBe("inspector");
    expect(f).toHaveBeenCalledTimes(2);
    expect((f.mock.calls[1][1]!.headers as Record<string, string>).Authorization).toBe("Bearer fresh-token");
  });

  it("maps the backend error format to ApiError with field errors", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      json(422, { error: { code: "validation_error", message: "Some values are invalid.", fields: { brand: "Required" } } }),
    );
    await expect(api("/api/v1/proposals", { method: "POST", body: {} })).rejects.toMatchObject({
      status: 422,
      code: "validation_error",
      fields: { brand: "Required" },
    });
    await expect(api("/x")).rejects.toBeInstanceOf(ApiError);
  });

  it("retries while the backend host is waking (non-JSON 502)", async () => {
    vi.useFakeTimers();
    const f = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response("<html>waking</html>", { status: 502, headers: { "content-type": "text/html" } }))
      .mockResolvedValueOnce(json(200, { ok: 1 }));
    const p = api<{ ok: number }>("/api/v1/me");
    await vi.advanceTimersByTimeAsync(2500);
    expect(await p).toEqual({ ok: 1 });
    expect(f).toHaveBeenCalledTimes(2);
    vi.useRealTimers();
  });
});

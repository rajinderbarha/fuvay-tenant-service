/**
 * UX-06 Round 2: first real automated tests for this app (no test framework
 * existed before this round — jest-expo + RNTL added, mirroring the pattern
 * mobile/staff-app used successfully in UX-05).
 *
 * Scope: the corrected api.ts contract layer (auth, catalog, ai-chat language
 * folding) — the foundational pieces this round's work touched.
 */
import { withLanguageInstruction, type ChatLanguage } from "../api";

describe("withLanguageInstruction", () => {
  it("returns the message unchanged when no language is selected", () => {
    expect(withLanguageInstruction("Hello")).toBe("Hello");
  });

  it("returns the message unchanged for English (the base app language)", () => {
    const en: ChatLanguage = { code: "en", englishName: "English", nativeName: "English", dir: "ltr" };
    expect(withLanguageInstruction("Hello", en)).toBe("Hello");
  });

  it("prefixes a real, backend-ignorable language instruction for non-English selections", () => {
    const hi: ChatLanguage = { code: "hi", englishName: "Hindi", nativeName: "हिन्दी", dir: "ltr" };
    const out = withLanguageInstruction("I need AC repair", hi);
    expect(out).toContain("Hindi");
    expect(out).toContain("हिन्दी");
    expect(out).toContain("hi");
    expect(out).toContain("I need AC repair");
  });

  it("never mutates canonical booking/job/service text — only prefixes it", () => {
    const pa: ChatLanguage = { code: "pa", englishName: "Punjabi", nativeName: "ਪੰਜਾਬੀ", dir: "ltr" };
    const original = "booking_id=abc123 status=assigned";
    const out = withLanguageInstruction(original, pa);
    expect(out.endsWith(original)).toBe(true);
  });
});

describe("aiConversationApi.sendMessage — language instruction is on EVERY request, not just available", () => {
  const realFetch = global.fetch;

  afterEach(() => { global.fetch = realFetch; jest.restoreAllMocks(); });

  function mockFetchCapturingBody() {
    const calls: { url: string; body: unknown }[] = [];
    global.fetch = jest.fn(async (url: any, opts: any) => {
      calls.push({ url: String(url), body: opts?.body ? JSON.parse(opts.body) : null });
      return {
        ok: true,
        json: async () => ({ data: { reply: "ok", tools_called: [], intent: "x", session: { id:"s1", customer_id:null, workflow_status:"active" } } }),
      } as Response;
    }) as unknown as typeof fetch;
    return calls;
  }

  it("includes the withLanguageInstruction-wrapped text for a non-English language on every send", async () => {
    const calls = mockFetchCapturingBody();
    const { aiConversationApi } = require("../api");
    const hi = { code:"hi", englishName:"Hindi", nativeName:"हिन्दी", dir:"ltr" as const };

    await aiConversationApi.sendMessage("session-1", "I need AC repair", hi);
    await aiConversationApi.sendMessage("session-1", "It stopped cooling yesterday", hi);

    expect(calls).toHaveLength(2);
    for (const call of calls) {
      expect(call.url).toContain("/v1/customer/ai-chat/sessions/session-1/messages");
      expect((call.body as { message:string }).message).toContain("Hindi");
      expect((call.body as { message:string }).message).toContain("हिन्दी");
    }
  });

  it("sends the plain message with no language wrapper when English/no language is selected", async () => {
    const calls = mockFetchCapturingBody();
    const { aiConversationApi } = require("../api");
    await aiConversationApi.sendMessage("session-1", "Hello");
    expect((calls[0].body as { message:string }).message).toBe("Hello");
  });
});

describe("api.ts module surface", () => {
  it("exports the real, corrected endpoint groups (contract-shape smoke test)", () => {
    const api = require("../api");
    // Auth: unified /v1/auth/login, no fake customer OTP endpoints.
    expect(typeof api.authApi.login).toBe("function");
    expect(api.authApi.requestOtp).toBeUndefined();
    expect(api.authApi.verifyOtp).toBeUndefined();
    // Real customer-scoped groups added/corrected this round.
    expect(typeof api.catalogApi.categories).toBe("function");
    expect(typeof api.fieldOpsJobsApi.list).toBe("function");
    expect(typeof api.aiConversationApi.createSession).toBe("function");
    expect(typeof api.aiConversationApi.sendMessage).toBe("function");
    // Legacy dead route must never be reintroduced.
    expect(api.reviewsApi.submit).toBeUndefined();
  });
});

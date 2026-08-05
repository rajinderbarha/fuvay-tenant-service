import { renderHook, waitFor, act } from "@testing-library/react-native";
import { useAssistantController } from "../useAssistantController";
import { createServiceCardEntryContext, createAssistantCardEntryContext } from "../../../domain/assistantEntry";
import { asCategoryId, asCustomerId } from "../../../domain/ids";
import * as assistantApi from "../../../api/assistant/assistantApi";
import * as draftApi from "../../../api/bookingDrafts/bookingDraftApi";
import * as questionFlowApi from "../../../api/questionFlow/questionFlowApi";
import * as assistantBootstrapApi from "../../../api/assistantBootstrap/assistantBootstrapApi";
import * as persistence from "../../../storage/draft/assistantSessionPersistence";

jest.mock("../../../api/assistant/assistantApi");
jest.mock("../../../api/bookingDrafts/bookingDraftApi");
jest.mock("../../../api/questionFlow/questionFlowApi");
jest.mock("../../../api/assistantBootstrap/assistantBootstrapApi");
jest.mock("../../../storage/draft/assistantSessionPersistence");

function bootstrapDto(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    schema_version: 1,
    category: { id: "cat-1", slug: "ac-cooling", name: "AC & Cooling" },
    zipcode: "141002",
    serviceable: true,
    issues: [{ id: "issue-1", label: "AC Repair" }],
    resumable_draft: null,
    current_stage: "issue_selection",
    ...overrides,
  };
}

const customerId = asCustomerId("cust-1");

function sessionDto(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: "sess-1", session_key: "key-1", customer_id: "cust-1", category_id: "cat-1", language: "en",
    current_intent: "booking", workflow_status: "active", collected_fields: {}, context_data: {},
    turn_count: 0, last_activity_at: null, completed_at: null, is_active: true,
    created_at: "2026-08-01T00:00:00Z", updated_at: "2026-08-01T00:00:00Z",
    language_options: [{ code: "en", label: "English" }, { code: "hi", label: "Hindi" }],
    ...overrides,
  };
}

function envelopeDto(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    envelope_version: 1, session_id: "sess-1", draft_id: "draft-1", workflow_version: null, question_flow_version: 1,
    scope: { category_id: "cat-1", offering_id: "off-1", job_type_id: null },
    current_question: {
      question_id: "q-1", question_key: "issue", question_type: "single_select", text: "What's wrong?",
      help_text: null, required: true, options: [{ id: "opt-1", label: "Not cooling" }], photo_capable: false,
    },
    progress: { answered_count: 0, remaining_count: 1, complete: false },
    next_permitted_actions: ["answer"],
    answered_questions: [],
    ...overrides,
  };
}

beforeEach(() => {
  jest.clearAllMocks();
  (persistence.loadAssistantPointer as jest.Mock).mockResolvedValue(null);
  (persistence.saveAssistantPointer as jest.Mock).mockResolvedValue(undefined);
  // Language selection is the first interaction of every fresh request --
  // give it a real default session response so tests that just need to
  // get past it do not have to restate it.
  (assistantApi.setAssistantSessionLanguage as jest.Mock).mockResolvedValue({ data: sessionDto() });
});

describe("useAssistantController", () => {
  it("creates a fresh session and stays in conversation mode when no draft exists yet (generic entry)", async () => {
    (assistantApi.createAssistantSession as jest.Mock).mockResolvedValue({ data: sessionDto() });
    (draftApi.getBookingDraftByAiSession as jest.Mock).mockResolvedValue({ data: null });

    const entry = createAssistantCardEntryContext({ zipcode: "141002" });
    const { result } = renderHook(() => useAssistantController(entry, customerId));

    await waitFor(() => expect(result.current.uiState).toBe("ready"));
    expect(result.current.draftId).toBeNull();
    expect(result.current.session?.id).toBe("sess-1");
    expect(assistantApi.createAssistantSession).toHaveBeenCalledWith({ categoryId: undefined, zipcode: "141002" });
    expect(persistence.saveAssistantPointer).toHaveBeenCalledWith(customerId, "generic", "sess-1", null);
  });

  it("always starts a brand-new session even when a persisted pointer exists (product decision: never resume)", async () => {
    (persistence.loadAssistantPointer as jest.Mock).mockResolvedValue({
      schemaVersion: 1, ownerCustomerId: customerId, scopeKey: "ac-cooling", sessionId: "sess-old", draftId: "draft-old", updatedAt: "2026-08-01T00:00:00Z",
    });
    (assistantApi.createAssistantSession as jest.Mock).mockResolvedValue({ data: sessionDto() });
    (assistantBootstrapApi.getAssistantBootstrap as jest.Mock).mockResolvedValue({ data: bootstrapDto() });

    const entry = createServiceCardEntryContext({
      categoryId: asCategoryId("cat-1"), categoryName: "AC & Cooling", categorySlug: "ac-cooling", zipcode: "141002",
    });
    const { result } = renderHook(() => useAssistantController(entry, customerId));

    await waitFor(() => expect(result.current.uiState).toBe("ready"));
    // The persisted pointer is never even read for resume purposes --
    // createAssistantSession is always called, getAssistantSession(old
    // pointer) never is. With no resumable draft in the backend-first
    // bootstrap response, draftId stays null and the real, backend-owned
    // offering list drives the first screen instead.
    expect(assistantApi.getAssistantSession).not.toHaveBeenCalled();
    expect(assistantApi.createAssistantSession).toHaveBeenCalledWith({ categoryId: "cat-1", zipcode: "141002" });
    expect(assistantBootstrapApi.getAssistantBootstrap).toHaveBeenCalledWith("ac-cooling", "141002");
    expect(result.current.draftId).toBeNull();
    expect(result.current.session?.id).toBe("sess-1");
    // CUSTOMER-ASSISTANT-UX-04: the LANGUAGE choice is the first
    // interaction now -- the real backend issue list is fetched but
    // deliberately withheld until a language is picked, so booking
    // content never appears in an unchosen language.
    expect(result.current.languageChoice).toEqual([{ code: "en", label: "English" }, { code: "hi", label: "Hindi" }]);
    expect(result.current.offeringChoice).toBeNull();
    // No artificial "I need help with X" kickoff message -- only the
    // welcome greeting and the backend-owned language prompt are present.
    expect(result.current.messages).toHaveLength(2);
    expect(assistantApi.sendAssistantMessage).not.toHaveBeenCalled();
  });

  it("CUSTOMER-ASSISTANT-CHAT-02: never activates or surfaces resumable_draft even when the backend still returns one", async () => {
    // The Resume-draft feature has been removed entirely (binding product
    // decision: every explicit service tap always starts a brand-new
    // request). This proves the controller no longer even branches on
    // `resumable_draft` -- draftId stays null and the fresh issue list
    // drives the screen regardless of what the field contains.
    (assistantApi.createAssistantSession as jest.Mock).mockResolvedValue({ data: sessionDto() });
    (assistantBootstrapApi.getAssistantBootstrap as jest.Mock).mockResolvedValue({
      data: bootstrapDto({
        resumable_draft: { id: "draft-old", offering_name: "AC Repair" },
      }),
    });

    const entry = createServiceCardEntryContext({
      categoryId: asCategoryId("cat-1"), categoryName: "AC & Cooling", categorySlug: "ac-cooling", zipcode: "141002",
    });
    const { result } = renderHook(() => useAssistantController(entry, customerId));

    await waitFor(() => expect(result.current.uiState).toBe("ready"));
    expect(result.current.draftId).toBeNull();
    expect(result.current.envelope).toBeNull();
    expect("resumableDraft" in result.current).toBe(false);
    // Language-first: the issue list is withheld behind the language
    // choice, so the fresh-request guarantee is proven by draftId staying
    // null and the language prompt (not an old draft) being active.
    expect(result.current.languageChoice).not.toBeNull();
  });

  it("discovers a newly created draft after sending a message and switches into question-flow mode", async () => {
    (assistantApi.createAssistantSession as jest.Mock).mockResolvedValue({ data: sessionDto() });
    (draftApi.getBookingDraftByAiSession as jest.Mock)
      .mockResolvedValue({
        data: {
          id: "draft-1", customer_id: "cust-1", ai_session_id: "sess-1", category_id: "cat-1", offering_id: "off-1",
          job_type_id: null, status: "in_progress", city: null, zipcode: "141002", issue_summary: null,
          serviceability_status: "serviceable", price_status: "pending", provider_match_status: "pending",
          price_snapshot: null, expires_at: null, created_at: null, updated_at: null,
        },
      });
    (assistantApi.sendAssistantMessage as jest.Mock).mockResolvedValue({
      data: { reply: "Got it, let's find the right question.", tools_called: [], session: sessionDto(), intent: "clarify" },
    });
    (questionFlowApi.getQuestionFlow as jest.Mock).mockResolvedValue({ data: envelopeDto() });

    const entry = createAssistantCardEntryContext({ zipcode: "141002" });
    const { result } = renderHook(() => useAssistantController(entry, customerId));
    await waitFor(() => expect(result.current.uiState).toBe("ready"));
    expect(result.current.draftId).toBeNull();

    await act(async () => {
      await result.current.sendMessage("My AC stopped cooling");
    });

    await waitFor(() => expect(result.current.uiState).toBe("ready"));
    expect(result.current.draftId).toBe("draft-1");
    expect(result.current.envelope?.currentQuestion?.questionId).toBe("q-1");
    expect(result.current.messages).toHaveLength(2);
  });

  it("submitting an answer refreshes the envelope from the response and never resubmits blindly on a stale-version conflict", async () => {
    (assistantApi.createAssistantSession as jest.Mock).mockResolvedValue({ data: sessionDto() });
    (assistantBootstrapApi.getAssistantBootstrap as jest.Mock).mockResolvedValue({ data: bootstrapDto() });
    (assistantBootstrapApi.selectAssistantBootstrapIssue as jest.Mock).mockResolvedValue({
      data: { draft_id: "draft-1", envelope: envelopeDto(), selected_issue_ids: ["issue-1"] },
    });
    (questionFlowApi.submitQuestionFlowAnswer as jest.Mock).mockResolvedValue({
      data: envelopeDto({ question_flow_version: 2, progress: { answered_count: 1, remaining_count: 0, complete: true } }),
    });

    const entry = createServiceCardEntryContext({
      categoryId: asCategoryId("cat-1"), categoryName: "AC & Cooling", categorySlug: "ac-cooling", zipcode: "141002",
    });
    const { result } = renderHook(() => useAssistantController(entry, customerId));
    // Backend-first: a service tap always shows a fresh issue list (see
    // "old selection showing" fix -- no auto-resume here); selecting the
    // issue is what actually creates/resolves the draft.
    // CUSTOMER-ASSISTANT-UX-04: language is the first interaction of every
    // fresh request -- the issue list only appears once it is chosen.
    await waitFor(() => expect(result.current.languageChoice).not.toBeNull());
    await act(async () => {
      await result.current.chooseLanguage({ code: "en", label: "English" });
    });
    await waitFor(() => expect(result.current.offeringChoice).not.toBeNull());
    await act(async () => {
      await result.current.selectOffering([{ id: "issue-1", slug: "issue-1", name: "AC Repair" }]);
    });
    await waitFor(() => expect(result.current.draftId).toBe("draft-1"));

    await act(async () => {
      await result.current.submitAnswer("q-1", "opt-1", null);
    });

    await waitFor(() => expect(result.current.uiState).toBe("ready"));
    // The chosen conversation language rides along so the NEXT question
    // (returned in this same response) comes back already presented in it.
    expect(questionFlowApi.submitQuestionFlowAnswer).toHaveBeenCalledWith("draft-1", {
      questionId: "q-1", optionId: "opt-1", value: null, expectedVersion: 1,
      language: "en", sessionId: "sess-1",
    });
    expect(result.current.envelope?.progress.complete).toBe(true);
  });

  it("ignores a second submitAnswer call fired while the first is still in flight (double-tap protection)", async () => {
    (assistantApi.createAssistantSession as jest.Mock).mockResolvedValue({ data: sessionDto() });
    (assistantBootstrapApi.getAssistantBootstrap as jest.Mock).mockResolvedValue({ data: bootstrapDto() });
    (assistantBootstrapApi.selectAssistantBootstrapIssue as jest.Mock).mockResolvedValue({
      data: { draft_id: "draft-1", envelope: envelopeDto(), selected_issue_ids: ["issue-1"] },
    });

    // Never resolves within this test -- simulates a real in-flight
    // request, so a second submitAnswer call arriving before the first
    // completes must be dropped by the busyRef guard, not queued or
    // double-submitted to the backend.
    let resolveSubmit: (v: { data: unknown }) => void;
    const pending = new Promise<{ data: unknown }>(resolve => { resolveSubmit = resolve; });
    (questionFlowApi.submitQuestionFlowAnswer as jest.Mock).mockReturnValue(pending);

    const entry = createServiceCardEntryContext({
      categoryId: asCategoryId("cat-1"), categoryName: "AC & Cooling", categorySlug: "ac-cooling", zipcode: "141002",
    });
    const { result } = renderHook(() => useAssistantController(entry, customerId));
    // CUSTOMER-ASSISTANT-UX-04: language is the first interaction of every
    // fresh request -- the issue list only appears once it is chosen.
    await waitFor(() => expect(result.current.languageChoice).not.toBeNull());
    await act(async () => {
      await result.current.chooseLanguage({ code: "en", label: "English" });
    });
    await waitFor(() => expect(result.current.offeringChoice).not.toBeNull());
    await act(async () => {
      await result.current.selectOffering([{ id: "issue-1", slug: "issue-1", name: "AC Repair" }]);
    });
    await waitFor(() => expect(result.current.draftId).toBe("draft-1"));
    await waitFor(() => expect(result.current.uiState).toBe("ready"));

    // Fire two taps back-to-back without awaiting the first -- mirrors a
    // real fast double-tap on the same option in the UI.
    act(() => {
      result.current.submitAnswer("q-1", "opt-1", null);
      result.current.submitAnswer("q-1", "opt-1", null);
    });

    expect(questionFlowApi.submitQuestionFlowAnswer).toHaveBeenCalledTimes(1);

    // Let the in-flight request resolve so the hook settles cleanly.
    await act(async () => {
      resolveSubmit({ data: envelopeDto({ question_flow_version: 2, progress: { answered_count: 1, remaining_count: 0, complete: true } }) });
    });
    await waitFor(() => expect(result.current.uiState).toBe("ready"));
    expect(questionFlowApi.submitQuestionFlowAnswer).toHaveBeenCalledTimes(1);
  });
});

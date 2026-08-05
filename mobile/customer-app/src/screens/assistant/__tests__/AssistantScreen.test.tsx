import React from "react";
import { Keyboard } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { act, fireEvent, waitFor } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { AssistantScreen } from "../AssistantScreen";
import * as controllerModule from "../useAssistantController";
import * as profileQueryModule from "../../../api/customer/useCustomerProfileQuery";
import * as homeQueryModule from "../../../api/home/useCustomerHomeQuery";
import { asCustomerId } from "../../../domain/ids";

/**
 * Regression tests for a physical-device-confirmed defect: AC Gas
 * Refilling simultaneously rendered a date-selection quick-reply AND the
 * required "What's happening with the cooling?" catalog question -- two
 * competing actionable groups on screen at once. These tests render the
 * REAL AssistantScreen with a controlled controller state (mocked at the
 * hook boundary, per this repo's HomeScreen.test.tsx convention) and
 * assert on the actual rendered tree, not just the controller's internal
 * state -- the bug lived in the screen's own rendering logic, not the
 * controller.
 */

const Stack = createNativeStackNavigator();

function renderAssistant() {
  return renderWithProviders(
    <NavigationContainer>
      <Stack.Navigator>
        <Stack.Screen name="Assistant" component={AssistantScreen} initialParams={undefined} />
        <Stack.Screen name="Home" component={() => null} />
        <Stack.Screen name="BookingReview" component={() => null} />
      </Stack.Navigator>
    </NavigationContainer>,
  );
}

function baseControllerState(overrides: Partial<ReturnType<typeof controllerModule.useAssistantController>> = {}) {
  return {
    uiState: "ready" as const,
    activityStage: null,
    session: {
      id: "sess-1", sessionKey: "key-1", categoryId: "cat-1", language: "en",
      languageOptions: [{ code: "en", label: "English" }], turnCount: 1, isActive: true, workflowStatus: "active",
    },
    draftId: "draft-1",
    envelope: null,
    messages: [],
    errorMessage: null,
    fallbackOffered: false,
    offeringChoice: null,
    languageChoice: null,
    priceSnapshot: null,
    sendMessage: jest.fn(),
    interpretFreeText: jest.fn(),
    interpretOfferingText: jest.fn(),
    selectOffering: jest.fn(),
    submitAnswer: jest.fn(),
    changeLanguage: jest.fn(),
    chooseLanguage: jest.fn(),
    continueWithGuidedFallback: jest.fn(),
    cancelCurrentOperation: jest.fn(),
    retry: jest.fn(),
    restart: jest.fn(),
    ...overrides,
  };
}

beforeEach(() => {
  jest.spyOn(profileQueryModule, "useCustomerProfileQuery").mockReturnValue({
    data: { id: asCustomerId("cust-1") },
  } as unknown as ReturnType<typeof profileQueryModule.useCustomerProfileQuery>);
  jest.spyOn(homeQueryModule, "useCustomerHomeQuery").mockReturnValue({
    data: { address: { zipcode: "140412" } },
  } as unknown as ReturnType<typeof homeQueryModule.useCustomerHomeQuery>);
});

describe("AssistantScreen -- single-active-question invariant", () => {
  it("renders exactly one actionable group when a catalog question is active AND an earlier message carries quick-replies", () => {
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({
      messages: [
        {
          id: "m-1", role: "assistant", content: "I've prepared your AC Gas Refilling request. When would you like the service done?",
          createdAt: null,
          quickReplies: [
            { label: "Today", value: "I'd like it on 2026-08-03 (Today)." },
            { label: "Tomorrow", value: "I'd like it on 2026-08-04 (Tomorrow)." },
            { label: "This weekend", value: "I'd like it on 2026-08-08 (This weekend)." },
          ],
        },
      ],
      envelope: {
        envelopeVersion: 1, sessionId: "sess-1", draftId: "draft-1" as never, questionFlowVersion: 1,
        scope: { categoryId: "cat-1", offeringId: "off-1", jobTypeId: "jt-1" },
        currentQuestion: {
          questionId: "q-1", questionKey: "cooling_symptom", questionType: "single_select",
          text: "What's happening with the cooling?", helpText: null, required: true,
          options: [
            { id: "opt-1", label: "Not cooling at all" }, { id: "opt-2", label: "Cooling weakly" },
            { id: "opt-3", label: "Warm air only" }, { id: "opt-4", label: "Ice forming on unit" },
          ],
          photoCapable: false, acceptsFreeText: false,
        },
        progress: { answeredCount: 0, remainingCount: 1, complete: false },
        nextPermittedActions: ["submit_answer"],
        answeredQuestions: [],
      },
    }));

    const { queryByText, getByText } = renderAssistant();

    // The one real, canonical question is shown.
    expect(getByText("What's happening with the cooling?")).toBeTruthy();
    expect(getByText("Not cooling at all")).toBeTruthy();

    // The date quick-replies attached to the earlier message must NOT
    // render while the catalog question owns the interaction -- this is
    // the exact defect: both were visible simultaneously.
    expect(queryByText("Today")).toBeNull();
    expect(queryByText("Tomorrow")).toBeNull();
    expect(queryByText("This weekend")).toBeNull();

    // The free-text composer must not render either -- this is a
    // tap-only question (acceptsFreeText: false).
    expect(queryByText("Type your answer")).toBeNull();
  });

  it("shows date quick-replies normally once there is no active catalog question", () => {
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({
      messages: [
        {
          id: "m-1", role: "assistant", content: "Great, got that. When would you like the service done?",
          createdAt: null,
          quickReplies: [{ label: "Today", value: "I'd like it on 2026-08-03 (Today)." }],
        },
      ],
      envelope: {
        envelopeVersion: 1, sessionId: "sess-1", draftId: "draft-1" as never, questionFlowVersion: 2,
        scope: { categoryId: "cat-1", offeringId: "off-1", jobTypeId: "jt-1" },
        currentQuestion: null,
        progress: { answeredCount: 1, remainingCount: 0, complete: true },
        nextPermittedActions: ["proceed_to_serviceability"],
        answeredQuestions: [{ questionId: "q-1", questionKey: "cooling_symptom", questionLabel: "What's happening with the cooling?", answerLabel: "Not cooling at all" }],
      },
    }));

    const { getByText } = renderAssistant();
    expect(getByText("Today")).toBeTruthy();
  });

  it("renders the free-text composer for a question that genuinely accepts free text", () => {
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({
      envelope: {
        envelopeVersion: 1, sessionId: "sess-1", draftId: "draft-1" as never, questionFlowVersion: 1,
        scope: { categoryId: "cat-1", offeringId: "off-1", jobTypeId: "jt-1" },
        currentQuestion: {
          questionId: "q-2", questionKey: "issue_detail", questionType: "text",
          text: "Please describe the issue in your own words.", helpText: null, required: true,
          options: [], photoCapable: false, acceptsFreeText: true,
        },
        progress: { answeredCount: 0, remainingCount: 1, complete: false },
        nextPermittedActions: ["submit_answer"],
        answeredQuestions: [],
      },
    }));

    const { getByPlaceholderText } = renderAssistant();
    expect(getByPlaceholderText("Add details…")).toBeTruthy();
  });
});

/**
 * Regression tests for the second physical-device report: the chatbot
 * "processing" experience read as a dashboard status panel (a large
 * top-of-screen banner, rotating phrases like "Understanding your
 * request…", "Your progress is safe", and a "Continue with guided
 * questions" button) rather than a natural chat. These assert on the real
 * rendered AssistantScreen tree, not the removed AssistantActivity
 * component in isolation -- the fix was deleting its use from this screen
 * entirely, so a test against AssistantActivity alone would prove nothing
 * about what the screen actually shows.
 */
describe("AssistantScreen -- inline chat processing (no top banner)", () => {
  it("never renders the old rotating-phrase/status-panel copy anywhere on screen", () => {
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({
      uiState: "submitting_answer",
      activityStage: "validating_answer",
      envelope: {
        envelopeVersion: 1, sessionId: "sess-1", draftId: "draft-1" as never, questionFlowVersion: 1,
        scope: { categoryId: "cat-1", offeringId: "off-1", jobTypeId: "jt-1" },
        currentQuestion: {
          questionId: "q-1", questionKey: "cooling_symptom", questionType: "single_select",
          text: "What's happening with the cooling?", helpText: null, required: true,
          options: [{ id: "opt-1", label: "Not cooling at all" }],
          photoCapable: false, acceptsFreeText: false,
        },
        progress: { answeredCount: 0, remainingCount: 1, complete: false },
        nextPermittedActions: ["submit_answer"],
        answeredQuestions: [],
      },
    }));

    const { queryByText } = renderAssistant();

    expect(queryByText(/understanding your request/i)).toBeNull();
    expect(queryByText(/checking details/i)).toBeNull();
    expect(queryByText(/your progress is safe/i)).toBeNull();
    expect(queryByText(/guided question/i)).toBeNull();
    expect(queryByText(/fallback/i)).toBeNull();
    expect(queryByText(/canonical question/i)).toBeNull();
    expect(queryByText(/backend question flow/i)).toBeNull();
  });

  it("shows the fixed inline typing indicator (accessible label, no changing text) while a question is being submitted", () => {
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({
      uiState: "submitting_answer",
      messages: [{ id: "m-1", role: "user", content: "Not cooling at all", createdAt: null }],
      envelope: null,
    }));

    const { getByLabelText } = renderAssistant();
    expect(getByLabelText("Assistant is responding")).toBeTruthy();
  });

  it("never shows 'Please wait…' in the composer while a free-text question is being submitted", () => {
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({
      uiState: "submitting_answer",
      envelope: {
        envelopeVersion: 1, sessionId: "sess-1", draftId: "draft-1" as never, questionFlowVersion: 1,
        scope: { categoryId: "cat-1", offeringId: "off-1", jobTypeId: "jt-1" },
        currentQuestion: {
          questionId: "q-2", questionKey: "issue_detail", questionType: "text",
          text: "Please describe the issue in your own words.", helpText: null, required: true,
          options: [], photoCapable: false, acceptsFreeText: true,
        },
        progress: { answeredCount: 0, remainingCount: 1, complete: false },
        nextPermittedActions: ["submit_answer"],
        answeredQuestions: [],
      },
    }));

    const { queryByPlaceholderText, queryByText } = renderAssistant();
    expect(queryByPlaceholderText("Please wait…")).toBeNull();
    expect(queryByText("Please wait…")).toBeNull();
  });

  it("immediately hides the option cards and echoes the tapped answer once a tap-only question is answered", async () => {
    let resolveSubmit: () => void;
    const pending = new Promise<void>(resolve => { resolveSubmit = resolve; });
    const submitAnswer = jest.fn().mockReturnValue(pending);

    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({
      submitAnswer,
      envelope: {
        envelopeVersion: 1, sessionId: "sess-1", draftId: "draft-1" as never, questionFlowVersion: 1,
        scope: { categoryId: "cat-1", offeringId: "off-1", jobTypeId: "jt-1" },
        currentQuestion: {
          questionId: "q-1", questionKey: "cooling_symptom", questionType: "single_select",
          text: "What's happening with the cooling?", helpText: null, required: true,
          options: [{ id: "opt-1", label: "Not cooling at all" }],
          photoCapable: false, acceptsFreeText: false,
        },
        progress: { answeredCount: 0, remainingCount: 1, complete: false },
        nextPermittedActions: ["submit_answer"],
        answeredQuestions: [],
      },
    }));

    const { getByText, queryByText, queryByRole } = renderAssistant();
    expect(getByText("What's happening with the cooling?")).toBeTruthy();

    fireEvent.press(getByText("Not cooling at all"));

    // The option card (with its own required/optional badge + title) must
    // disappear the instant the tap fires -- the tapped label now shows as
    // a normal transcript bubble instead, not a second, duplicate copy
    // sitting inside a greyed-out card.
    await waitFor(() => {
      expect(queryByText("What's happening with the cooling?")).toBeNull();
    });
    expect(submitAnswer).toHaveBeenCalledWith("q-1", "opt-1", null);

    await act(async () => {
      resolveSubmit!();
      await pending;
    });
  });
});

/**
 * CUSTOMER-CHAT-UX-03: real bug fixed here -- a genuine `free_text`
 * canonical question (no backend options at all -- the ONLY kind of
 * question that ever leaves the composer mounted, see `composerAllowed`)
 * must submit the raw typed text directly through `submitAnswer` (the
 * same `QuestionFlowService.submit_answer` path a tap uses), never
 * through `interpretFreeText` (DeepSeek's constrained OPTION-matching
 * interpreter) or the general `sendMessage` chat endpoint. Routing a
 * genuinely free-text answer through the option-matching interpreter was
 * confirmed live to always reject ordinary text ("I'm sorry, I didn't
 * quite catch that...") and re-ask the same question as a duplicate chat
 * message, alongside the still-showing QuestionCard.
 */
describe("AssistantScreen -- backend-first free-text routing", () => {
  it("submits a genuine free-text answer directly via submitAnswer -- never interpretFreeText or sendMessage", async () => {
    const interpretFreeText = jest.fn().mockResolvedValue(undefined);
    const sendMessage = jest.fn().mockResolvedValue(undefined);
    const submitAnswer = jest.fn().mockResolvedValue(undefined);
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({
      interpretFreeText, sendMessage, submitAnswer,
      envelope: {
        envelopeVersion: 1, sessionId: "sess-1", draftId: "draft-1" as never, questionFlowVersion: 1,
        scope: { categoryId: "cat-1", offeringId: "off-1", jobTypeId: "jt-1" },
        currentQuestion: {
          questionId: "q-2", questionKey: "issue_detail", questionType: "text",
          text: "Please describe the issue in your own words.", helpText: null, required: true,
          options: [], photoCapable: false, acceptsFreeText: true,
        },
        progress: { answeredCount: 0, remainingCount: 1, complete: false },
        nextPermittedActions: ["submit_answer"],
        answeredQuestions: [],
      },
    }));

    const { getByPlaceholderText, getByLabelText } = renderAssistant();
    const input = getByPlaceholderText("Add details…");
    fireEvent.changeText(input, "It's leaking from the top");
    fireEvent.press(getByLabelText("Send message"));

    await waitFor(() => expect(submitAnswer).toHaveBeenCalledWith("q-2", null, "It's leaking from the top"));
    expect(interpretFreeText).not.toHaveBeenCalled();
    expect(sendMessage).not.toHaveBeenCalled();
  });

  it("routes free text to sendMessage (not interpretFreeText) when no canonical question is active", async () => {
    const interpretFreeText = jest.fn().mockResolvedValue(undefined);
    const sendMessage = jest.fn().mockResolvedValue(undefined);
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({
      interpretFreeText, sendMessage, envelope: null,
    }));

    const { getByPlaceholderText, getByLabelText } = renderAssistant();
    const input = getByPlaceholderText("Type your answer");
    fireEvent.changeText(input, "I need help with AC");
    fireEvent.press(getByLabelText("Send message"));

    await waitFor(() => expect(sendMessage).toHaveBeenCalledWith("I need help with AC"));
    expect(interpretFreeText).not.toHaveBeenCalled();
  });
});

/**
 * Regression tests for the backend-first Booking Assistant
 * re-architecture: the FIRST visible booking choice (offering selection)
 * must come directly from `assistant-bootstrap`, never a synthetic
 * "I need help with X" DeepSeek kickoff message and never a DeepSeek-
 * chosen offering list.
 */
describe("AssistantScreen -- backend-first offering selection", () => {
  it("renders backend-provided offerings as tap options, never an artificial kickoff message", () => {
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({
      draftId: null,
      envelope: null,
      messages: [{ id: "offering-prompt-sess-1", role: "assistant", content: "What type of Air Conditioning service do you need?", createdAt: null }],
      offeringChoice: {
        categoryName: "Air Conditioning", categorySlug: "air-conditioning",
        offerings: [
          { id: "off-1", slug: "ac-gas-refilling", name: "AC Gas Refilling" },
          { id: "off-2", slug: "ac-installation", name: "AC Installation" },
        ],
      },
    }));

    const { getByText, queryByText } = renderAssistant();

    expect(getByText("What type of Air Conditioning service do you need?")).toBeTruthy();
    expect(getByText("AC Gas Refilling")).toBeTruthy();
    expect(getByText("AC Installation")).toBeTruthy();
    // No artificial customer-side kickoff bubble.
    expect(queryByText(/I need help with/i)).toBeNull();
  });

  it("tapping an offering calls selectOffering directly -- never sendMessage or interpretFreeText", () => {
    const selectOffering = jest.fn().mockResolvedValue(undefined);
    const sendMessage = jest.fn().mockResolvedValue(undefined);
    const interpretFreeText = jest.fn().mockResolvedValue(undefined);
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({
      draftId: null, envelope: null, selectOffering, sendMessage, interpretFreeText,
      offeringChoice: {
        categoryName: "Air Conditioning", categorySlug: "air-conditioning",
        offerings: [{ id: "off-2", slug: "ac-installation", name: "AC Installation" }],
      },
    }));

    const { getByText } = renderAssistant();
    // Multi-select: a tap toggles the checkmark; Continue submits whatever
    // is currently selected (one or more real issues -- spec: "add
    // multiple problem").
    fireEvent.press(getByText("AC Installation"));
    fireEvent.press(getByText("Continue"));

    expect(selectOffering).toHaveBeenCalledWith([{ id: "off-2", slug: "ac-installation", name: "AC Installation" }]);
    expect(sendMessage).not.toHaveBeenCalled();
    expect(interpretFreeText).not.toHaveBeenCalled();
  });

  it("selecting more than one issue submits all of them together", () => {
    const selectOffering = jest.fn().mockResolvedValue(undefined);
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({
      draftId: null, envelope: null, selectOffering,
      offeringChoice: {
        categoryName: "Air Conditioning", categorySlug: "air-conditioning",
        offerings: [
          { id: "issue-1", slug: "issue-1", name: "AC Not Cooling" },
          { id: "issue-2", slug: "issue-2", name: "Water Leakage" },
        ],
      },
    }));

    const { getByText } = renderAssistant();
    fireEvent.press(getByText("AC Not Cooling"));
    fireEvent.press(getByText("Water Leakage"));
    fireEvent.press(getByText("Continue with 2 issues"));

    expect(selectOffering).toHaveBeenCalledWith([
      { id: "issue-1", slug: "issue-1", name: "AC Not Cooling" },
      { id: "issue-2", slug: "issue-2", name: "Water Leakage" },
    ]);
  });

  // CUSTOMER-APP-KEYBOARD-01: issue/offering selection is now a strictly
  // tap-only stage -- superseding the earlier "type instead of tap an
  // offering" design. Physical-device evidence showed a keyboard left
  // open from a prior screen covering the lower issue options with
  // nothing tap-only about it; the composer must not mount at all here,
  // not merely be present-but-unused.
  it("does not render the composer during issue/offering selection", () => {
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({
      draftId: null, envelope: null,
      offeringChoice: {
        categoryName: "Air Conditioning", categorySlug: "air-conditioning",
        offerings: [{ id: "off-1", slug: "ac-gas-refilling", name: "AC Gas Refilling" }],
      },
    }));

    const { queryByPlaceholderText } = renderAssistant();
    expect(queryByPlaceholderText("Type your answer")).toBeNull();
  });
});

/**
 * Regression test for the real physical-device navigation failure mode:
 * `AssistantScreen` is mounted as a TAB screen inside a bottom-tab
 * navigator (`CustomerTabs`), while "BookingReview" is registered one
 * level up, on the ROOT stack (`CustomerAppNavigator`) -- confirmed by
 * reading `CustomerTabs.tsx`/`CustomerAppNavigator.tsx`/`routeTypes.ts`.
 * This mirrors that exact real nesting (tab navigator nested inside a
 * stack that also owns "BookingReview") rather than the single flat stack
 * the other tests in this file use, so a "missing nested navigator" bug
 * -- calling `.navigate()` on the wrong navigator instance -- would
 * actually be caught here.
 */
describe("AssistantScreen -- Booking Review navigation (real nested-navigator shape)", () => {
  it("navigates to the root stack's BookingReview screen with the real draft/session IDs once every question is answered", () => {
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({
      draftId: "draft-42",
      session: {
        id: "sess-99", sessionKey: "key-1", categoryId: "cat-1", language: "en",
        languageOptions: [{ code: "en", label: "English" }], turnCount: 3, isActive: true, workflowStatus: "active",
      },
      envelope: {
        envelopeVersion: 1, sessionId: "sess-99", draftId: "draft-42" as never, questionFlowVersion: 2,
        scope: { categoryId: "cat-1", offeringId: "off-1", jobTypeId: "jt-1" },
        currentQuestion: null,
        progress: { answeredCount: 1, remainingCount: 0, complete: true },
        nextPermittedActions: ["proceed_to_serviceability"],
        answeredQuestions: [{ questionId: "q-1", questionKey: "cooling_symptom", questionLabel: "What's happening with the cooling?", answerLabel: "Not cooling at all" }],
      },
    }));

    const Tab = createBottomTabNavigator();
    const RootStack = createNativeStackNavigator();
    let capturedRoute: string | undefined;
    let capturedParams: unknown;

    function CustomerTabsStub() {
      return (
        <Tab.Navigator>
          <Tab.Screen name="Assistant" component={AssistantScreen} />
        </Tab.Navigator>
      );
    }
    function BookingReviewStub(props: { route?: { name: string; params: unknown } }) {
      capturedRoute = props.route?.name;
      capturedParams = props.route?.params;
      return null;
    }

    const { getByText } = renderWithProviders(
      <NavigationContainer>
        <RootStack.Navigator>
          <RootStack.Screen name="CustomerTabs" component={CustomerTabsStub} />
          <RootStack.Screen name="BookingReview" component={BookingReviewStub} />
        </RootStack.Navigator>
      </NavigationContainer>,
    );

    fireEvent.press(getByText("Continue to review"));

    expect(capturedRoute).toBe("BookingReview");
    expect(capturedParams).toEqual({ draftId: "draft-42", aiSessionId: "sess-99" });
  });
});

/**
 * CUSTOMER-APP-KEYBOARD-01 / CUSTOMER-ASSISTANT-CHAT-02: physical-device
 * iPhone reports -- the keyboard opened automatically on Assistant
 * launch, without the customer tapping any field, and covered the lower
 * issue options. Root cause: the composer's `TextInput` was mounted
 * (present, just visually de-prioritized) during every tap-only stage
 * rather than being genuinely absent from the tree, and nothing dismissed
 * a keyboard left open by a previous screen when the Assistant regained
 * focus. A second, related report showed a "Continue your X request?"
 * Resume-draft card rendering underneath an active required question --
 * the whole Resume-draft feature (component, controller state/actions,
 * bootstrap's `resumable_draft` read) has since been removed entirely per
 * the binding product decision that every explicit service tap always
 * starts a brand-new request (see useAssistantController.ts), so that
 * failure mode is now structurally impossible rather than merely patched.
 * These tests assert the composer's TextInput is never rendered during a
 * tap-only stage.
 */
describe("AssistantScreen -- CUSTOMER-APP-KEYBOARD-01 (tap-only composer absence)", () => {
  it("never renders a Resume-draft card -- the feature has been removed entirely", () => {
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({
      draftId: null, envelope: null,
      offeringChoice: {
        categoryName: "Air Conditioning", categorySlug: "air-conditioning",
        offerings: [{ id: "off-1", slug: "ac-installation", name: "New AC Installation" }],
      },
    }));

    const { queryByText } = renderAssistant();
    expect(queryByText(/continue previous booking/i)).toBeNull();
    expect(queryByText(/continue your .* request/i)).toBeNull();
    expect(queryByText(/start a new request/i)).toBeNull();
  });

  it("does not render a TextInput for a single-select tap-only question", () => {
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({
      envelope: {
        envelopeVersion: 1, sessionId: "sess-1", draftId: "draft-1" as never, questionFlowVersion: 1,
        scope: { categoryId: "cat-1", offeringId: "off-1", jobTypeId: "jt-1" },
        currentQuestion: {
          questionId: "q-1", questionKey: "brand", questionType: "single_select",
          text: "Which AC brand?", helpText: null, required: true,
          options: [{ id: "opt-1", label: "LG" }, { id: "opt-2", label: "Samsung" }],
          photoCapable: false, acceptsFreeText: false,
        },
        progress: { answeredCount: 0, remainingCount: 1, complete: false },
        nextPermittedActions: ["submit_answer"],
        answeredQuestions: [],
      },
    }));

    const { queryByPlaceholderText } = renderAssistant();
    expect(queryByPlaceholderText("Type your answer")).toBeNull();
  });

  it("does not render a TextInput for a multi-select tap-only question", () => {
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({
      envelope: {
        envelopeVersion: 1, sessionId: "sess-1", draftId: "draft-1" as never, questionFlowVersion: 1,
        scope: { categoryId: "cat-1", offeringId: "off-1", jobTypeId: "jt-1" },
        currentQuestion: {
          questionId: "q-1", questionKey: "symptoms", questionType: "multi_select",
          text: "Which symptoms apply?", helpText: null, required: true,
          options: [{ id: "opt-1", label: "Noise" }, { id: "opt-2", label: "Water leakage" }],
          photoCapable: false, acceptsFreeText: false,
        },
        progress: { answeredCount: 0, remainingCount: 1, complete: false },
        nextPermittedActions: ["submit_answer"],
        answeredQuestions: [],
      },
    }));

    const { queryByPlaceholderText } = renderAssistant();
    expect(queryByPlaceholderText("Type your answer")).toBeNull();
  });

  it("dismisses the keyboard when closing the Assistant", () => {
    const dismissSpy = jest.spyOn(Keyboard, "dismiss");
    jest.spyOn(profileQueryModule, "useCustomerProfileQuery").mockReturnValue({
      data: { id: asCustomerId("cust-1") },
    } as never);
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({}));

    const { getByLabelText } = renderAssistant();
    dismissSpy.mockClear();
    fireEvent.press(getByLabelText("Close assistant"));

    expect(dismissSpy).toHaveBeenCalled();
  });
});

/**
 * CUSTOMER-ASSISTANT-CHAT-03: real physical-device report -- typing a
 * free-text reply to Question 3 (after Brand and Capacity had already
 * been answered by tap) rendered that chat exchange ABOVE the
 * already-answered Brand/Capacity rows, even though it happened
 * chronologically AFTER them. Root cause: chat messages and answered-
 * question rows came from two independently-ordered arrays that were
 * naively concatenated (all answered rows, then all messages) instead of
 * genuinely interleaved by when each was first seen. These tests assert
 * the actual rendered order in the transcript, not just that both pieces
 * of content exist somewhere on screen.
 */
describe("AssistantScreen -- CUSTOMER-ASSISTANT-CHAT-03 (single chronological feed)", () => {
  it("keeps a later free-text exchange visually after earlier answered questions, not before them", () => {
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({
      messages: [
        { id: "m-1", role: "user", content: "Test", createdAt: null },
        { id: "m-2", role: "assistant", content: "I'm sorry, I didn't quite catch that.", createdAt: null },
      ],
      envelope: {
        envelopeVersion: 1, sessionId: "sess-1", draftId: "draft-1" as never, questionFlowVersion: 3,
        scope: { categoryId: "cat-1", offeringId: "off-1", jobTypeId: "jt-1" },
        currentQuestion: {
          questionId: "q-3", questionKey: "issue_detail", questionType: "text",
          text: "Please share any additional details about the issue.", helpText: null, required: true,
          options: [], photoCapable: false, acceptsFreeText: true,
        },
        progress: { answeredCount: 2, remainingCount: 1, complete: false },
        nextPermittedActions: ["submit_answer"],
        answeredQuestions: [
          { questionId: "q-1", questionKey: "brand", questionLabel: "Which AC brand?", answerLabel: "LG" },
          { questionId: "q-2", questionKey: "capacity_ton", questionLabel: "What is the AC capacity (in tons)?", answerLabel: "1 Ton" },
        ],
      },
    }));

    const { getAllByText, getByText } = renderAssistant();
    // Every real piece of content is present...
    expect(getByText("Test")).toBeTruthy();
    expect(getByText("I'm sorry, I didn't quite catch that.")).toBeTruthy();
    expect(getByText("Which AC brand?")).toBeTruthy();
    expect(getByText("What is the AC capacity (in tons)?")).toBeTruthy();
    // ...and in an inverted FlatList, the rendered `data` order IS the
    // real chronological order the customer perceives (data[0] renders
    // visually newest/bottom-most). The free-text exchange happened
    // AFTER Brand/Capacity were answered, so it must appear EARLIER in
    // the underlying data (closer to index 0) than either answered row.
    const allBubbleTexts = getAllByText(/Test|didn't quite catch|Which AC brand|AC capacity/).map(el => el.props.children);
    const testIndex = allBubbleTexts.findIndex(t => t === "Test");
    const brandIndex = allBubbleTexts.findIndex(t => t === "Which AC brand?");
    const capacityIndex = allBubbleTexts.findIndex(t => t === "What is the AC capacity (in tons)?");
    expect(testIndex).toBeGreaterThanOrEqual(0);
    expect(brandIndex).toBeGreaterThan(testIndex);
    expect(capacityIndex).toBeGreaterThan(testIndex);
  });
});

/**
 * CUSTOMER-CHAT-UX-03: physical-device report -- entering "Test" against
 * a genuine free-text question ("Please share any additional details
 * about the issue") produced a DeepSeek rejection ("I'm sorry, I didn't
 * quite catch that...") and re-asked the same question as a duplicate
 * chat message, because the composer routed the answer through the
 * OPTION-matching interpreter instead of `submitAnswer`. Also covers the
 * "completed answers become chat bubbles, not faded form cards" defect --
 * `AnsweredQuestionRow` (a bordered, disabled-looking card) has been
 * removed entirely; an answered question now renders as a plain
 * assistant bubble (the question) immediately followed by a plain
 * customer bubble (the answer), exactly like ordinary chat history.
 */
describe("AssistantScreen -- CUSTOMER-CHAT-UX-03 (no DeepSeek apology, answers as chat bubbles)", () => {
  it("never renders a DeepSeek apology or a duplicate question after a genuine free-text answer is accepted", () => {
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({
      envelope: {
        envelopeVersion: 1, sessionId: "sess-1", draftId: "draft-1" as never, questionFlowVersion: 4,
        scope: { categoryId: "cat-1", offeringId: "off-1", jobTypeId: "jt-1" },
        currentQuestion: null,
        progress: { answeredCount: 3, remainingCount: 0, complete: true },
        nextPermittedActions: ["proceed_to_serviceability"],
        answeredQuestions: [
          { questionId: "q-1", questionKey: "brand", questionLabel: "Which AC brand?", answerLabel: "LG" },
          { questionId: "q-2", questionKey: "capacity_ton", questionLabel: "What is the AC capacity (in tons)?", answerLabel: "1 Ton" },
          { questionId: "q-3", questionKey: "issue_detail", questionLabel: "Please share any additional details about the issue.", answerLabel: "Test" },
        ],
      },
    }));

    const { queryByText, getAllByText } = renderAssistant();
    expect(queryByText(/didn't quite catch/i)).toBeNull();
    // The answer bubble for the free-text question, not a second question
    // (it may also legitimately appear again in the booking summary).
    expect(getAllByText("Test").length).toBeGreaterThan(0);
    expect(getAllByText("Please share any additional details about the issue.").length).toBeGreaterThan(0);
  });

  it("exposes a header refresh action that starts a genuinely new request", () => {
    const restart = jest.fn();
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({ restart }));

    const { getByLabelText } = renderAssistant();
    fireEvent.press(getByLabelText("Start a new request"));
    expect(restart).toHaveBeenCalled();
  });

  it("renders completed Brand/Capacity answers as plain chat bubbles, not a bordered form card", () => {
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({
      envelope: {
        envelopeVersion: 1, sessionId: "sess-1", draftId: "draft-1" as never, questionFlowVersion: 2,
        scope: { categoryId: "cat-1", offeringId: "off-1", jobTypeId: "jt-1" },
        currentQuestion: {
          questionId: "q-3", questionKey: "issue_detail", questionType: "text",
          text: "Please share any additional details about the issue.", helpText: null, required: true,
          options: [], photoCapable: false, acceptsFreeText: true,
        },
        progress: { answeredCount: 2, remainingCount: 1, complete: false },
        nextPermittedActions: ["submit_answer"],
        answeredQuestions: [
          { questionId: "q-1", questionKey: "brand", questionLabel: "Which AC brand?", answerLabel: "LG" },
          { questionId: "q-2", questionKey: "capacity_ton", questionLabel: "What is the AC capacity (in tons)?", answerLabel: "1.5 Ton" },
        ],
      },
    }));

    const { getByText } = renderAssistant();
    // The question and its answer both render as ordinary chat bubbles.
    expect(getByText("Which AC brand?")).toBeTruthy();
    expect(getByText("LG")).toBeTruthy();
    expect(getByText("What is the AC capacity (in tons)?")).toBeTruthy();
    expect(getByText("1.5 Ton")).toBeTruthy();
  });
});

/**
 * CUSTOMER-ASSISTANT-UX-04 Part 1/2: the chatbot-language choice is the
 * FIRST interaction of every fresh booking request -- shown in the
 * conversation itself as full-width stacked options, before any issue or
 * Brand content, so a customer never sees booking content in a language
 * they haven't chosen. The options are entirely backend-derived
 * (`build_language_options`, ZIP-aware); this screen never fabricates,
 * reorders or filters them, and never offers Regional/Automatic/device
 * language.
 */
describe("AssistantScreen -- CUSTOMER-ASSISTANT-UX-04 (language-first)", () => {
  const LANGUAGES = [
    { code: "en", label: "English" },
    { code: "hi", label: "हिन्दी" },
    { code: "pa", label: "ਪੰਜਾਬੀ" },
  ];

  it("shows the language prompt and all three backend languages before any issue content", () => {
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({
      draftId: null, envelope: null, offeringChoice: null,
      languageChoice: LANGUAGES,
      messages: [{ id: "language-prompt-sess-1", role: "assistant", content: "Choose your preferred language", createdAt: null }],
    }));

    const { getByText, getAllByText, getByLabelText, queryByLabelText, queryByText } = renderAssistant();
    expect(getByText("Choose your preferred language")).toBeTruthy();
    // Each language renders as its own tappable option. "English" also
    // legitimately appears in the header language chip, so assert on the
    // option row itself (accessibility label) rather than raw text.
    for (const l of LANGUAGES) {
      expect(getByLabelText(l.label)).toBeTruthy();
      expect(getAllByText(l.label).length).toBeGreaterThan(0);
    }
    // No booking content, and none of the forbidden pseudo-languages.
    expect(queryByText("What do you need help with?")).toBeNull();
    // None of the forbidden pseudo-languages is ever offered as a
    // selectable option (asserted against the option rows themselves --
    // the header's unrelated "Saved automatically" caption is not a
    // language choice).
    expect(queryByLabelText(/regional/i)).toBeNull();
    expect(queryByLabelText(/automatic/i)).toBeNull();
    expect(queryByLabelText(/device language/i)).toBeNull();
  });

  it("does not mount the composer while the language choice is pending", () => {
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({
      draftId: null, envelope: null, languageChoice: LANGUAGES,
    }));
    const { queryByPlaceholderText } = renderAssistant();
    expect(queryByPlaceholderText("Type your answer")).toBeNull();
    expect(queryByPlaceholderText("Add details…")).toBeNull();
  });

  it("tapping a language calls chooseLanguage with that exact backend option", () => {
    const chooseLanguage = jest.fn();
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({
      draftId: null, envelope: null, languageChoice: LANGUAGES, chooseLanguage,
    }));

    const { getByText } = renderAssistant();
    fireEvent.press(getByText("ਪੰਜਾਬੀ"));
    expect(chooseLanguage).toHaveBeenCalledWith({ code: "pa", label: "ਪੰਜਾਬੀ" });
  });

  it("renders language options as full-width rows meeting the 56pt minimum touch height", () => {
    jest.spyOn(controllerModule, "useAssistantController").mockReturnValue(baseControllerState({
      draftId: null, envelope: null, languageChoice: LANGUAGES,
    }));

    const { getByLabelText } = renderAssistant();
    for (const l of LANGUAGES) {
      const row = getByLabelText(l.label);
      const style = typeof row.props.style === "function"
        ? row.props.style({ pressed: false })
        : row.props.style;
      const flat = Array.isArray(style) ? Object.assign({}, ...style.flat(Infinity).filter(Boolean)) : style;
      expect(flat.minHeight).toBeGreaterThanOrEqual(56);
      expect(flat.alignSelf).toBe("stretch");
    }
  });
});

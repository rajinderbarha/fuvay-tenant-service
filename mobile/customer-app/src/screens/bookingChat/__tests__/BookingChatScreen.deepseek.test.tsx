import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { AppProviders } from "../../../providers/AppProviders";
import { BookingChatScreen } from "../BookingChatScreen";
import * as controllerModule from "../../assistant/useAssistantController";
import * as profileModule from "../../../api/customer/useCustomerProfileQuery";
import * as homeModule from "../../../api/home/useCustomerHomeQuery";
import { asCustomerId } from "../../../domain/ids";

jest.mock("../../assistant/useAssistantController");
jest.mock("../../../api/customer/useCustomerProfileQuery");
jest.mock("../../../api/home/useCustomerHomeQuery");
jest.mock("../useBookingChatAddress", () => ({
  useBookingChatAddress: () => ({
    resolvedAddressId: null, addresses: [], loading: false, submitting: false,
    error: null, loadAddresses: jest.fn(), pickExisting: jest.fn(), createNew: jest.fn(),
  }),
}));

const OPTION_QUESTION = {
  questionId: "q-brand",
  text: "Which AC brand do you have?",
  acceptsFreeText: false,
  options: [{ id: "o-lg", label: "LG" }, { id: "o-voltas", label: "Voltas" }],
};
const FREE_TEXT_QUESTION = {
  questionId: "q-details",
  text: "Please share any additional details about the issue.",
  acceptsFreeText: true,
  options: [],
};

function controller(overrides: Record<string, unknown> = {}) {
  return {
    uiState: "ready",
    messages: [],
    envelope: null,
    offeringChoice: null,
    draftId: "d-1",
    activityTrace: [],
    activityStage: null,
    errorMessage: null,
    submitAnswer: jest.fn(),
    interpretFreeText: jest.fn(),
    interpretOfferingText: jest.fn(),
    selectOffering: jest.fn(),
    restart: jest.fn(),
    retry: jest.fn(),
    ...overrides,
  };
}

const Tab = createBottomTabNavigator();

/** Mounted with real service-card params: without them the screen shows its
 * category picker instead of the conversation, which is correct behaviour but
 * not what these tests are about. */
function renderChat(overrides: Record<string, unknown> = {}) {
  (controllerModule.useAssistantController as jest.Mock).mockReturnValue(controller(overrides));
  return render(
    <AppProviders>
      <NavigationContainer>
        <Tab.Navigator screenOptions={{ headerShown: false }}>
          <Tab.Screen
            name="Assistant"
            component={BookingChatScreen}
            initialParams={{
              source: "service_card",
              categoryId: "cat-1",
              categoryName: "Air Conditioning",
              categorySlug: "air-conditioning",
              zipcode: "141001",
              existingDraftId: null,
              preselectedIssueId: null,
            }}
          />
        </Tab.Navigator>
      </NavigationContainer>
    </AppProviders>,
  );
}

/**
 * DeepSeek's two constrained interpreters were built, reachable and working --
 * and never called by the live screen: 752 successful calls in
 * ai_llm_call_logs, none in the two days of bookings before this was wired.
 * Typing was only possible on a question that had no options, and the assistant
 * never once helped a customer answer one that did.
 *
 * These tests pin each destination, because the failure mode is silent: routing
 * to the wrong one still "works", it just quietly stops using the model (or,
 * the earlier bug, asks it to match text against nothing and rejects every
 * answer).
 */
describe("BookingChatScreen — where a typed message goes", () => {
  beforeEach(() => {
    (profileModule.useCustomerProfileQuery as jest.Mock).mockReturnValue({
      data: { id: asCustomerId("c-1"), displayName: "Rajinder" },
    });
    (homeModule.useCustomerHomeQuery as jest.Mock).mockReturnValue({
      data: { address: { zipcode: "141001", city: "Ludhiana" }, bookableCategories: [] },
      isPending: false,
    });
  });
  afterEach(() => jest.clearAllMocks());

  it("asks DeepSeek to match a typed answer against a question's real options", () => {
    const interpretFreeText = jest.fn();
    const submitAnswer = jest.fn();
    renderChat({
      interpretFreeText, submitAnswer,
      envelope: { currentQuestion: OPTION_QUESTION, answeredQuestions: [], progress: { complete: false } },
    });

    fireEvent.changeText(screen.getByLabelText("Type or tap an option above"), "it's a voltas");
    fireEvent.press(screen.getByLabelText("Send answer"));

    expect(interpretFreeText).toHaveBeenCalledWith("it's a voltas");
    // Never the raw submit path: that would store "it's a voltas" as the answer
    // to an option question, bypassing the canonical option ids.
    expect(submitAnswer).not.toHaveBeenCalled();
  });

  it("submits a genuine free-text answer directly, without consulting DeepSeek", () => {
    // There are no options to match against. An earlier version asked anyway,
    // and the model rejected every answer and re-asked the same question.
    const interpretFreeText = jest.fn();
    const submitAnswer = jest.fn();
    renderChat({
      interpretFreeText, submitAnswer,
      envelope: { currentQuestion: FREE_TEXT_QUESTION, answeredQuestions: [], progress: { complete: false } },
    });

    fireEvent.changeText(screen.getByLabelText("Type your answer"), "it rattles after ten minutes");
    fireEvent.press(screen.getByLabelText("Send answer"));

    expect(submitAnswer).toHaveBeenCalledWith("q-details", null, "it rattles after ten minutes");
    expect(interpretFreeText).not.toHaveBeenCalled();
  });

  it("lets the customer describe the problem instead of only tapping an issue", () => {
    const interpretOfferingText = jest.fn();
    renderChat({
      interpretOfferingText,
      draftId: null,
      offeringChoice: {
        categoryName: "Air Conditioning", categorySlug: "air-conditioning",
        offerings: [{ id: "i-1", slug: "i-1", name: "AC Not Cooling" }],
      },
    });

    fireEvent.changeText(screen.getByLabelText("Describe the problem"), "my ac is not cooling at all");
    fireEvent.press(screen.getByLabelText("Send answer"));

    expect(interpretOfferingText).toHaveBeenCalledWith("my ac is not cooling at all");
  });

  it("offers no input when nothing would read the text", () => {
    // A composer with no destination invites typing into a void.
    renderChat({ envelope: null, offeringChoice: null, draftId: "d-1" });
    expect(screen.queryByLabelText(/Type|Describe/)).toBeNull();
  });

  it("does not send an empty or whitespace-only message", () => {
    const interpretFreeText = jest.fn();
    renderChat({
      interpretFreeText,
      envelope: { currentQuestion: OPTION_QUESTION, answeredQuestions: [], progress: { complete: false } },
    });
    fireEvent.changeText(screen.getByLabelText("Type or tap an option above"), "   ");
    fireEvent.press(screen.getByLabelText("Send answer"));
    expect(interpretFreeText).not.toHaveBeenCalled();
  });

  it("blocks a second send while the model is still thinking", () => {
    const interpretFreeText = jest.fn();
    renderChat({
      interpretFreeText,
      uiState: "assistant_processing",
      envelope: { currentQuestion: OPTION_QUESTION, answeredQuestions: [], progress: { complete: false } },
    });
    fireEvent.changeText(screen.getByLabelText("Type or tap an option above"), "voltas");
    fireEvent.press(screen.getByLabelText("Send answer"));
    expect(interpretFreeText).not.toHaveBeenCalled();
  });
});

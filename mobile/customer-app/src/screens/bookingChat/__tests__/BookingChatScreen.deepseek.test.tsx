import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { AppProviders } from "../../../providers/AppProviders";
import { BookingChatScreen } from "../BookingChatScreen";
import * as controllerModule from "../../assistant/useAssistantController";
import * as profileModule from "../../../api/customer/useCustomerProfileQuery";
import * as homeModule from "../../../api/home/useCustomerHomeQuery";
import { asCustomerId } from "../../../domain/ids";
import AsyncStorage from "@react-native-async-storage/async-storage";

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

function renderBareAssistant(overrides: Record<string, unknown> = {}) {
  (controllerModule.useAssistantController as jest.Mock).mockReturnValue(controller(overrides));
  return render(
    <AppProviders>
      <NavigationContainer>
        <Tab.Navigator screenOptions={{ headerShown: false }}>
          <Tab.Screen name="Assistant" component={BookingChatScreen} />
          <Tab.Screen name="Home" component={() => null} />
        </Tab.Navigator>
      </NavigationContainer>
    </AppProviders>,
  );
}

describe("BookingChatScreen -- shared service location", () => {
  beforeEach(() => {
    (profileModule.useCustomerProfileQuery as jest.Mock).mockReturnValue({
      data: { id: asCustomerId("c-1"), displayName: "Rajinder" },
    });
    (homeModule.useCustomerHomeQuery as jest.Mock).mockReturnValue({
      data: {
        address: null,
        bookableCategories: [{ categoryId: "cat-1", name: "Air Conditioning", slug: "air-conditioning" }],
      },
      isPending: false,
    });
  });

  afterEach(async () => {
    await AsyncStorage.removeItem("customer_app_service_location_v1");
    jest.clearAllMocks();
  });

  it("uses the PIN selected on Home when the center Assistant tab opens directly", async () => {
    await AsyncStorage.setItem("customer_app_service_location_v1", "140412");
    renderBareAssistant();

    expect(await screen.findByText("Air Conditioning")).toBeTruthy();
    expect(screen.queryByText("Choose your location first")).toBeNull();
    await waitFor(() => {
      expect(homeModule.useCustomerHomeQuery).toHaveBeenLastCalledWith("140412");
    });
  });
});

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

describe("an empty issue list", () => {
  it("says so instead of leaving a dead screen after the greeting", () => {
    // Real bug: the bot greeted the customer, asked "What do you need help with?",
    // and then rendered a chip row with no chips -- nothing after the animated text,
    // no explanation, no way forward. A category genuinely can have nothing bookable
    // at a ZIP, so it has to say that.
    renderChat({
      offeringChoice: {
        categoryName: "Air Conditioning",
        categorySlug: "air-conditioning",
        offerings: [],
      },
    });
    expect(screen.getByText("Nothing to book here yet")).toBeTruthy();
    expect(screen.getByText("This service is not currently available in ZIP code 141001.")).toBeTruthy();
    expect(screen.getByText("Choose another service")).toBeTruthy();
  });

  it("still shows the real issues when there are any", () => {
    renderChat({
      offeringChoice: {
        categoryName: "Air Conditioning",
        categorySlug: "air-conditioning",
        offerings: [{ id: "i-1", slug: "i-1", name: "AC Not Cooling" }],
      },
    });
    expect(screen.getByText("AC Not Cooling")).toBeTruthy();
    expect(screen.queryByText("Nothing to book here yet")).toBeNull();
  });
});

describe("a failure the customer can see", () => {
  it("shows the controller's error with a way to retry", () => {
    // Real bug: `errorMessage` was set on every failure path -- a failed bootstrap, a
    // rejected answer, a dead session -- and NOTHING rendered it. The typing dots
    // stopped and the conversation ended: nothing after the animated text, no reason,
    // no retry. A booking flow cannot afford a silent failure; the customer's only
    // remaining move is to assume the app is broken.
    const retry = jest.fn();
    renderChat({ errorMessage: "We couldn't reach the booking service.", retry });

    expect(screen.getByText("We couldn't reach the booking service.")).toBeTruthy();
    fireEvent.press(screen.getByText("Try again"));
    expect(retry).toHaveBeenCalled();
  });

  it("shows a recovered stale-question notice quietly, not as a failure", () => {
    // The controller sets this after successfully refreshing a question whose choices
    // moved on -- the answer was not lost and nothing needs retrying. Rendering it
    // through the error card put a red alert and a "Try again" button on a flow that had
    // just worked, which is how a working assistant came to look broken.
    renderChat({ notice: "The choices were updated, so here is the latest question." });

    expect(screen.getByText("The choices were updated, so here is the latest question.")).toBeTruthy();
    expect(screen.queryByText("Try again")).toBeNull();
  });

  it("shows no error card when nothing has failed", () => {
    renderChat({});
    expect(screen.queryByText("Try again")).toBeNull();
  });
});

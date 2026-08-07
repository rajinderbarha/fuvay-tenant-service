import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { BookingDetailsSearchLauncher } from "../BookingDetailsSearchLauncher";

const Stack = createNativeStackNavigator();

let lastParams: unknown = "not-navigated";
function CapturingBookingsScreen(props: { route?: { params: unknown } }) {
  lastParams = props.route?.params;
  return null;
}

function render() {
  lastParams = "not-navigated";
  return renderWithProviders(
    <NavigationContainer>
      <Stack.Navigator>
        <Stack.Screen name="Detail" component={BookingDetailsSearchLauncher} />
        <Stack.Screen name="Bookings" component={CapturingBookingsScreen} />
      </Stack.Navigator>
    </NavigationContainer>,
  );
}

describe("BookingDetailsSearchLauncher", () => {
  it("hands a typed search term to My Bookings rather than searching nothing locally", () => {
    // This screen is one already-open booking; there is nothing here to
    // search against, so the term must travel to the real list.
    const { getByLabelText } = render();
    const input = getByLabelText("Search your bookings");
    fireEvent.changeText(input, "AC Service");
    fireEvent(input, "submitEditing");
    expect(lastParams).toEqual({ initialSearch: "AC Service" });
  });

  it("does not navigate on an empty submit", () => {
    const { getByLabelText } = render();
    fireEvent(getByLabelText("Search your bookings"), "submitEditing");
    expect(lastParams).toBe("not-navigated");
  });

  it("opens My Bookings' filter sheet directly, without requiring a search term first", () => {
    const { getByLabelText } = render();
    fireEvent.press(getByLabelText("Filter bookings"));
    expect(lastParams).toEqual({ openFilter: true });
  });
});

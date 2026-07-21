import React from "react";
import { Text } from "react-native";
import { render, waitFor, fireEvent } from "@testing-library/react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { AuthProvider, useAuth } from "../AuthContext";

jest.mock("../../lib/api", () => {
  const actual = jest.requireActual("../../lib/api");
  return {
    ...actual,
    authApi: {
      login: jest.fn(),
      me: jest.fn(),
      logout: jest.fn(),
    },
  };
});
import { authApi } from "../../lib/api";

function Probe() {
  const { user, loading, login, logout, error } = useAuth();
  return (
    <>
      <Text testID="loading">{String(loading)}</Text>
      <Text testID="user">{user ? user.full_name : "none"}</Text>
      <Text testID="error">{error ?? "none"}</Text>
      <Text testID="do-login" onPress={() => login("a@b.com", "pw").catch(()=>{})}>login</Text>
      <Text testID="do-logout" onPress={() => logout()}>logout</Text>
    </>
  );
}

describe("AuthContext (real email/password contract this round wired up)", () => {
  beforeEach(async () => {
    await AsyncStorage.clear();
    jest.clearAllMocks();
  });

  it("starts logged-out with no stored token", async () => {
    const { getByTestId } = render(<AuthProvider><Probe/></AuthProvider>);
    await waitFor(() => expect(getByTestId("loading").props.children).toBe("false"));
    expect(getByTestId("user").props.children).toBe("none");
  });

  it("logs in via authApi.login and persists the session", async () => {
    (authApi.login as jest.Mock).mockResolvedValue({
      access_token: "tok123",
      user: { id: "cust1", full_name: "Priya Sharma" },
    });
    const { getByTestId } = render(<AuthProvider><Probe/></AuthProvider>);
    await waitFor(() => expect(getByTestId("loading").props.children).toBe("false"));

    fireEvent.press(getByTestId("do-login"));

    await waitFor(() => expect(getByTestId("user").props.children).toBe("Priya Sharma"));
    expect(authApi.login).toHaveBeenCalledWith("a@b.com", "pw");
    expect(await AsyncStorage.getItem("serviceos_customer_token")).toBe("tok123");
  });

  it("surfaces a real error message on failed login rather than silently succeeding", async () => {
    (authApi.login as jest.Mock).mockRejectedValue(new Error("Invalid email or password."));
    const { getByTestId } = render(<AuthProvider><Probe/></AuthProvider>);
    await waitFor(() => expect(getByTestId("loading").props.children).toBe("false"));

    fireEvent.press(getByTestId("do-login"));

    await waitFor(() => expect(getByTestId("error").props.children).toBe("Invalid email or password."));
    expect(getByTestId("user").props.children).toBe("none");
  });

  it("logout clears the persisted session", async () => {
    (authApi.login as jest.Mock).mockResolvedValue({
      access_token: "tok123",
      user: { id: "cust1", full_name: "Priya Sharma" },
    });
    (authApi.logout as jest.Mock).mockResolvedValue(undefined);
    const { getByTestId } = render(<AuthProvider><Probe/></AuthProvider>);
    await waitFor(() => expect(getByTestId("loading").props.children).toBe("false"));
    fireEvent.press(getByTestId("do-login"));
    await waitFor(() => expect(getByTestId("user").props.children).toBe("Priya Sharma"));

    fireEvent.press(getByTestId("do-logout"));

    await waitFor(() => expect(getByTestId("user").props.children).toBe("none"));
    expect(await AsyncStorage.getItem("serviceos_customer_token")).toBeNull();
  });
});

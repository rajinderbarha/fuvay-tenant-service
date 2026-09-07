import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

const { login, completeMfaLogin } = vi.hoisted(() => ({ login: vi.fn(), completeMfaLogin: vi.fn() }));
vi.mock("../../lib/api", () => ({ authApi: { login, completeMfaLogin } }));
import LoginPage from "./page";

beforeEach(() => { vi.clearAllMocks(); localStorage.clear(); });

it("waits for MFA verification without storing an undefined access token", async () => {
  login.mockResolvedValue({ mfa_required: true, mfa_challenge_token: "challenge" });
  completeMfaLogin.mockRejectedValue(new Error("Invalid MFA code."));
  render(<LoginPage />);
  fireEvent.change(screen.getByLabelText("Email or mobile number"), { target: { value: "owner@example.com" } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "password" } });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
  const code = await screen.findByLabelText("Authenticator or backup code");
  expect(localStorage.getItem("serviceos_tenant_token")).toBeNull();
  fireEvent.change(code, { target: { value: "123456" } });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
  await waitFor(() => expect(completeMfaLogin).toHaveBeenCalledWith("challenge", "123456", false));
  expect(await screen.findByText("Invalid MFA code.")).toBeInTheDocument();
  expect(localStorage.getItem("serviceos_tenant_token")).toBeNull();
});

it("preserves the real authentication error", async () => {
  login.mockRejectedValue(new Error("Account is locked. Try again later."));
  render(<LoginPage />);
  fireEvent.change(screen.getByLabelText("Email or mobile number"), { target: { value: "owner@example.com" } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "password" } });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
  expect(await screen.findByText("Account is locked. Try again later.")).toBeInTheDocument();
});

import React from "react";
import { beforeEach, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import StaffLoginPage from "./page";

const mocks = vi.hoisted(() => ({ login: vi.fn(), push: vi.fn() }));
vi.mock("../../../lib/api", () => ({ authApi: { login: mocks.login } }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mocks.push }) }));
vi.mock("../../../lib/authTimeline", () => ({ authTimeline: vi.fn() }));
beforeEach(() => { cleanup(); vi.clearAllMocks(); localStorage.clear(); });

async function signIn() {
  render(<StaffLoginPage/>);
  fireEvent.change(screen.getByPlaceholderText("technician@example.com"), { target: { value: "team@example.test" } });
  fireEvent.change(document.querySelector('input[type="password"]')!, { target: { value: "Fixture-Only42!" } });
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Sign In" })); });
}

it("requires a new password and clears old refresh credentials before showing the staff app", async () => {
  localStorage.setItem("serviceos_tenant_refresh", "old-refresh");
  mocks.login.mockResolvedValue({ access_token: "temporary-session", refresh_token: null, requires_password_change: true,
    user: { id: "member-user", role: "technician", tenant_id: "tenant", force_password_change: true }, tenant: { name: "Workspace" } });
  await signIn();
  await waitFor(() => expect(mocks.push).toHaveBeenCalledWith("/change-password-required"));
  expect(mocks.push).not.toHaveBeenCalledWith("/staff/dashboard");
  expect(localStorage.getItem("serviceos_tenant_refresh")).toBeNull();
  expect(localStorage.getItem("serviceos_force_pw_change")).toBe("1");
});

it("allows ordinary staff login after the password has been changed", async () => {
  localStorage.setItem("serviceos_force_pw_change", "1");
  mocks.login.mockResolvedValue({ access_token: "normal-session", refresh_token: "new-refresh", requires_password_change: false,
    user: { id: "member-user", role: "staff", tenant_id: "tenant" }, tenant: { name: "Workspace" } });
  await signIn();
  await waitFor(() => expect(mocks.push).toHaveBeenCalledWith("/staff/dashboard"));
  expect(localStorage.getItem("serviceos_force_pw_change")).toBeNull();
});

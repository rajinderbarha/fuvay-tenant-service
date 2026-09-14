import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  me: vi.fn(), routing: vi.fn(), replace: vi.fn(), clearSession: vi.fn(),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: mocks.replace }) }));
vi.mock("../../../../../lib/api", () => ({
  authApi: { me: mocks.me },
  homeServicesSetupOverviewApi: { getRouting: mocks.routing },
  clearSession: mocks.clearSession,
  ServiceOSError: class extends Error {},
}));

import HomeServicesSetupLayout from "./layout";

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  mocks.me.mockResolvedValue({ role: "tenant_owner" });
});

it("never renders setup or queries its lifecycle without a login session", async () => {
  render(<HomeServicesSetupLayout><p>Private setup editor</p></HomeServicesSetupLayout>);
  await waitFor(() => expect(mocks.clearSession).toHaveBeenCalledOnce());
  expect(mocks.routing).not.toHaveBeenCalled();
  expect(screen.queryByText("Private setup editor")).not.toBeInTheDocument();
});

it.each([
  ["TENANT_DASHBOARD", "/dashboard"],
  ["HOME_SERVICES_ACTIVATION", "/onboarding/activation-center"],
  ["HOME_SERVICES_UNDER_REVIEW", "/onboarding/application-status"],
  ["RESTRICTED_WORKSPACE", "/dashboard"],
])("redirects %s without rendering the old setup editor", async (next_destination, path) => {
  localStorage.setItem("serviceos_tenant_token", "token");
  mocks.routing.mockResolvedValue({ next_destination });
  render(<HomeServicesSetupLayout><p>Private setup editor</p></HomeServicesSetupLayout>);
  await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith(path));
  expect(screen.queryByText("Private setup editor")).not.toBeInTheDocument();
});

it.each(["HOME_SERVICES_SETUP_OVERVIEW", "HOME_SERVICES_CHANGES_REQUESTED"])(
  "allows %s to complete its original setup", async next_destination => {
    localStorage.setItem("serviceos_tenant_token", "token");
    mocks.routing.mockResolvedValue({ next_destination });
    render(<HomeServicesSetupLayout><p>Private setup editor</p></HomeServicesSetupLayout>);
    expect(await screen.findByText("Private setup editor")).toBeInTheDocument();
    expect(mocks.replace).not.toHaveBeenCalled();
  },
);

it("fails closed when the authoritative lifecycle cannot be checked", async () => {
  localStorage.setItem("serviceos_tenant_token", "token");
  mocks.routing.mockRejectedValue(new Error("offline"));
  render(<HomeServicesSetupLayout><p>Private setup editor</p></HomeServicesSetupLayout>);
  expect(await screen.findByRole("alert")).toHaveTextContent("couldn't verify your setup status");
  expect(screen.queryByText("Private setup editor")).not.toBeInTheDocument();
});

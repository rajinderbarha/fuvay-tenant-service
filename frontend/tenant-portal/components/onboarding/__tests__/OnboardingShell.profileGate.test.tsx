import React from "react";
import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
const { getOverview } = vi.hoisted(() => ({ getOverview: vi.fn() }));
vi.mock("../../../lib/api", () => ({ homeServicesSetupOverviewApi: { getOverview }, authApi: { me: async () => ({ full_name: "Owner" }) }, providerNotifApi: { unreadCount: async () => ({ unread_count: 0 }) }, clearSession: vi.fn() }));
vi.mock("../../../hooks/useTenant", () => ({ useTenant: () => ({}) }));
vi.mock("../../../hooks/useTheme", () => ({ useTheme: () => ({ theme: "dark", toggle: vi.fn() }) }));
vi.mock("../../layout/CreditPill", () => ({ CreditPill: () => null }));
vi.mock("../../layout/Breadcrumbs", () => ({ Breadcrumbs: () => null }));
vi.mock("../../shared/ProfilePhotoUploader", () => ({ DefaultAvatar: () => null }));
import { OnboardingShell } from "../OnboardingShell";

it("locks direct access to later steps until the saved profile is complete", async () => {
  getOverview.mockResolvedValue({ sections: [{ key: "BUSINESS_PROFILE", status: "not_started" }], progress: { percentage: 0, total_required: 5, completed_required: 0 } });
  render(<OnboardingShell activeNav="documents"><p>Document editor</p></OnboardingShell>);
  expect(await screen.findByText("Complete Business Profile first")).toBeInTheDocument();
  expect(screen.queryByText("Document editor")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Documents" })).toHaveAttribute("aria-disabled", "true");
});

it("unlocks the next step when the backend confirms profile completion", async () => {
  getOverview.mockResolvedValue({ sections: [{ key: "BUSINESS_PROFILE", status: "complete" }], progress: { percentage: 20, total_required: 5, completed_required: 1 } });
  render(<OnboardingShell activeNav="documents"><p>Document editor</p></OnboardingShell>);
  expect(await screen.findByText("Document editor")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Documents" })).not.toHaveAttribute("aria-disabled");
});

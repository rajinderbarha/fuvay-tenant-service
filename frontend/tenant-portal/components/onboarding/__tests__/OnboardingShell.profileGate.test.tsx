import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
const { getOverview } = vi.hoisted(() => ({ getOverview: vi.fn() }));
vi.mock("../../../lib/api", () => ({ homeServicesSetupOverviewApi: { getOverview }, authApi: { me: async () => ({ full_name: "Owner" }) }, providerNotifApi: { unreadCount: async () => ({ unread_count: 0 }) }, clearSession: vi.fn() }));
vi.mock("../../../hooks/useTenant", () => ({ useTenant: () => ({}) }));
vi.mock("../../../hooks/useTheme", () => ({ useTheme: () => ({ theme: "dark", toggle: vi.fn() }) }));
vi.mock("../../layout/CreditPill", () => ({ CreditPill: () => null }));
vi.mock("../../layout/Breadcrumbs", () => ({ Breadcrumbs: () => null }));
vi.mock("../../shared/ProfilePhotoUploader", () => ({ DefaultAvatar: () => null }));
import { OnboardingShell } from "../OnboardingShell";
import { SETUP_STEPS } from "../../../lib/setup-sequence";

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

it("locks the plan direct URL until services are complete even if progress is hidden", async () => {
  getOverview.mockResolvedValue({ vertical: { status: "draft_setup" }, sections: SETUP_STEPS.map(([key], index) => ({ key, status: index < 2 ? "complete" : "not_started" })), progress: { percentage: 29, total_required: 7, completed_required: 2 } });
  render(<OnboardingShell activeNav="plan" showProgress={false}><p>Plan editor</p></OnboardingShell>);
  expect(await screen.findByText("Complete Services & Pricing first")).toBeInTheDocument();
  expect(screen.queryByText("Plan editor")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Technician Seat Plan" })).toHaveAttribute("aria-disabled", "true");
  getOverview.mockResolvedValue({ vertical: { status: "draft_setup" }, sections: SETUP_STEPS.map(([key], index) => ({ key, status: index < 3 ? "complete" : "not_started" })), progress: { percentage: 43, total_required: 7, completed_required: 3 } });
  fireEvent(window, new Event("home-services-setup-updated"));
  expect(await screen.findByText("Plan editor")).toBeInTheDocument();
});

it("keeps later editors closed if readiness cannot be checked", async () => {
  getOverview.mockRejectedValue(new Error("offline"));
  render(<OnboardingShell activeNav="finance"><p>Finance editor</p></OnboardingShell>);
  expect(await screen.findByText("Could not check setup progress")).toBeInTheDocument();
  expect(screen.queryByText("Finance editor")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
});

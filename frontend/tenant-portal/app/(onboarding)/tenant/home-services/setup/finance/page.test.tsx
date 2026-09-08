import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import FinancePage from "./page";
import { SETUP_STEPS } from "../../../../../../lib/setup-sequence";

const api = vi.hoisted(() => ({ get: vi.fn(), save: vi.fn(), getOverview: vi.fn(), push: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: api.push }) }));
vi.mock("../../../../../../lib/api", () => ({
  financeReadinessApi: { get: api.get, save: api.save },
  ServiceOSError: class extends Error {},
  homeServicesSetupOverviewApi: { getOverview: api.getOverview },
  authApi: { me: async () => ({ full_name: "Owner" }) },
  providerNotifApi: { unreadCount: async () => ({ unread_count: 0 }) }, clearSession: vi.fn(),
}));
vi.mock("../../../../../../hooks/useTenant", () => ({ useTenant: () => ({}) }));
vi.mock("../../../../../../hooks/useTheme", () => ({ useTheme: () => ({ theme: "light", toggle: vi.fn() }) }));
vi.mock("../../../../../../components/layout/CreditPill", () => ({ CreditPill: () => null }));
vi.mock("../../../../../../components/layout/Breadcrumbs", () => ({ Breadcrumbs: () => null }));
vi.mock("../../../../../../components/shared/ProfilePhotoUploader", () => ({ DefaultAvatar: () => null }));

const manifest = (complete = false) => ({
  readiness_percentage: complete ? 100 : 0, setup_complete: complete,
  checks: { direct_methods_selected: complete, confirmation_configured: complete, invoice_details_complete: complete },
  direct_payment: { accepts_cash: true, accepts_upi: true, accepts_card_at_service_location: false,
    accepts_bank_transfer: false, payment_confirmation_required: true, issue_customer_receipt: true,
    invoice_business_name: null, invoice_prefix: complete ? "TEST" : null },
  invoice_defaults: { business_name: "Test AC Service", gstin: null, gstin_verified: false },
  policy: { revenue_model: "Provider commission", customer_pays: "Provider directly", job_settlement: "Outside Fuvay",
    pricing_ownership: "Tenant business", provider_commission_pct: 10, policy_version: "LIVE" },
  notice: "Customers pay your business directly.",
});
const overview = (complete = false) => ({
  vertical: { status: "draft_setup" },
  sections: SETUP_STEPS.map(([key]) => ({ key, status: key === "FINANCE_READINESS" && !complete ? "not_started" : "complete" })),
  progress: { percentage: complete ? 100 : 83, total_required: 6, completed_required: complete ? 6 : 5 },
});

beforeEach(() => {
  vi.resetAllMocks();
  api.get.mockResolvedValue(manifest());
  api.getOverview.mockResolvedValue(overview());
  api.save.mockImplementation(async () => {
    api.getOverview.mockResolvedValue(overview(true));
    return manifest(true);
  });
});
afterEach(cleanup);
async function openAndFill() {
  render(<FinancePage/>);
  const prefix = await screen.findByLabelText("Invoice prefix");
  fireEvent.change(prefix, { target: { value: "test" } });
  return prefix;
}

it("shows draft completion while keeping unsaved finance out of the sidebar and Review gate", async () => {
  await openAndFill();
  expect(screen.getByText("100%")).toBeInTheDocument();
  expect(screen.getByText("Finance readiness (unsaved draft)")).toBeInTheDocument();
  expect(screen.getByText("Ready to save")).toBeInTheDocument();
  expect(screen.getByRole("progressbar", { name: "Setup completion" })).toHaveAttribute("aria-valuenow", "83");
  expect(screen.getByRole("link", { name: "Review & Submit" })).toHaveAttribute("aria-disabled", "true");
  expect(api.save).not.toHaveBeenCalled();
});

it("refreshes the actual onboarding shell and unlocks Review after saving", async () => {
  await openAndFill();
  fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
  await screen.findByText("Finance details saved. This step is 100% complete.");
  await waitFor(() => expect(screen.getByRole("link", { name: "Review & Submit" })).not.toHaveAttribute("aria-disabled"));
  expect(screen.getByRole("progressbar", { name: "Setup completion" })).toHaveAttribute("aria-valuenow", "100");
  expect(api.save).toHaveBeenCalledWith(expect.objectContaining({ invoice_business_name: "Test AC Service", invoice_prefix: "TEST", accepts_card_at_service_location: false, accepts_bank_transfer: false }));
  expect(api.push).not.toHaveBeenCalled();
});

it("waits for a successful server confirmation before continuing and prevents edits during save", async () => {
  const prefix = await openAndFill();
  let resolveSave!: (value: ReturnType<typeof manifest>) => void;
  api.save.mockReturnValueOnce(new Promise(resolve => { resolveSave = resolve; }));
  fireEvent.click(screen.getByRole("button", { name: "Save & continue" }));
  expect(prefix).toBeDisabled();
  expect(screen.getByRole("button", { name: "Cash Enabled" })).toBeDisabled();
  expect(api.push).not.toHaveBeenCalled();
  await act(async () => { resolveSave(manifest(true)); });
  expect(api.push).toHaveBeenCalledWith("/tenant/home-services/setup/review");
});

it("does not navigate when the backend still reports incomplete finance", async () => {
  await openAndFill();
  api.save.mockResolvedValueOnce(manifest(false));
  fireEvent.click(screen.getByRole("button", { name: "Save & continue" }));
  await screen.findByText("Finance setup is not complete yet. Check the remaining items and save again.");
  expect(api.push).not.toHaveBeenCalled();
});

it("preserves failed-save edits without unlocking Review or reporting saved completion", async () => {
  const prefix = await openAndFill();
  api.save.mockRejectedValueOnce(new Error("offline"));
  fireEvent.click(screen.getByRole("button", { name: "Save & continue" }));
  await screen.findByText("Could not save finance readiness. Please try again.");
  expect(prefix).toHaveValue("TEST");
  expect(screen.getByRole("link", { name: "Review & Submit" })).toHaveAttribute("aria-disabled", "true");
  expect(api.push).not.toHaveBeenCalled();
  expect(api.getOverview).toHaveBeenCalledTimes(1);
});

it("shows persisted completion on a fresh page load", async () => {
  api.get.mockResolvedValue(manifest(true));
  api.getOverview.mockResolvedValue(overview(true));
  render(<FinancePage/>);
  await screen.findByText("Ready for review");
  expect(screen.queryByText("Finance readiness (unsaved draft)")).not.toBeInTheDocument();
  expect(screen.getByLabelText("Invoice prefix")).toHaveValue("TEST");
});

it("does not count whitespace-only invoice details as a complete draft", async () => {
  const prefix = await openAndFill();
  fireEvent.change(prefix, { target: { value: "   " } });
  expect(screen.getByText("67%")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Save & continue" }));
  expect(screen.getByText("Enter the invoice business name and invoice prefix before continuing.")).toBeInTheDocument();
  expect(api.save).not.toHaveBeenCalled();
});

it("displays load failures with a working Retry instead of an endless skeleton", async () => {
  api.get.mockRejectedValueOnce(new Error("offline"));
  render(<FinancePage/>);
  await screen.findByText("We couldn't load your finance readiness.");
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(await screen.findByLabelText("Invoice prefix")).toBeInTheDocument();
});

import React from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  listAvailable: vi.fn(), listEnabled: vi.fn(), getPricingPolicy: vi.fn(),
  updatePricingPolicy: vi.fn(), updateEnabledService: vi.fn(), saveDraft: vi.fn(),
  getAvailableTypes: vi.fn(), getAvailableBrands: vi.fn(), getTypePricing: vi.fn(),
  getBrandPricing: vi.fn(), setTypes: vi.fn(), setBrands: vi.fn(),
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("../../../lib/api", () => ({
  homeServicesSetupApi: api, ServiceOSError: class extends Error {},
}));
vi.mock("../../onboarding/OnboardingShell", () => ({
  OnboardingShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
vi.mock("../ServicesSetupProgress", () => ({ ServicesSetupProgress: () => null }));
vi.mock("../ServiceRequirementsPanel", () => ({ ServiceRequirementsPanel: () => null }));
vi.mock("../InlineDimensionPricingEditor", () => ({
  InlineDimensionPricingEditor: React.forwardRef(() => <div>Dimension prices</div>),
}));
import ServicesPricingSetupPage from "../ServicesPricingSetupPage";

const consultation = {
  service_id: "master", service_name: "AC advice", service_group_id: "group",
  service_group_name: "Air conditioning", job_type: "consultation",
  job_type_id: "consultation", offering_key: "master:consultation",
  pricing_model: "fixed", admin_ready: true,
};
const enrolled = {
  tenant_service_id: "tenant-service", master_service_id: "master",
  job_type: "consultation", job_type_id: "consultation", is_enabled: true,
  setup_status: "draft", warranty_days: 5, requires_type: true, requires_brand: true,
  tenant_min_price: null, tenant_max_price: null, tenant_visit_fee: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  api.listAvailable.mockResolvedValue({ services: [consultation] });
  api.listEnabled.mockResolvedValue({ services: [enrolled] });
  api.getPricingPolicy.mockResolvedValue({ consultation_fee: 299 });
  api.updatePricingPolicy.mockResolvedValue({ consultation_fee: 399 });
  api.getAvailableTypes.mockResolvedValue({ types: [{ service_type_id: "split", name: "Split AC", is_enabled: true }] });
  api.getAvailableBrands.mockResolvedValue({ brands: [{ brand_id: "brand", name: "Test brand", is_enabled: true }] });
  api.updateEnabledService.mockResolvedValue(enrolled);
  api.saveDraft.mockResolvedValue(enrolled);
});

it("shows one provider-level fee, with matching controls but no per-consultation amount", async () => {
  render(<ServicesPricingSetupPage />);
  const settings = await screen.findByRole("region", { name: "Provider-wide consultation fee" });
  expect(within(settings).getByLabelText("Consultation fee")).toHaveValue(299);
  expect(screen.getAllByLabelText("Consultation fee")).toHaveLength(1);
  await screen.findByRole("checkbox", { name: "Split AC" });
  expect(screen.getByRole("checkbox", { name: "Test brand" })).toBeChecked();
  expect(screen.queryByText("Minimum price")).not.toBeInTheDocument();
  expect(screen.queryByText("Service price")).not.toBeInTheDocument();
  expect(screen.queryByText("Dimension prices")).not.toBeInTheDocument();
  expect(api.getTypePricing).not.toHaveBeenCalled();
  expect(api.getBrandPricing).not.toHaveBeenCalled();
});

it("saves consultation offering settings without a per-service price or visit fee", async () => {
  render(<ServicesPricingSetupPage />);
  await screen.findByRole("checkbox", { name: "Split AC" });
  fireEvent.click(screen.getByRole("button", { name: "Save as draft" }));
  await waitFor(() => expect(api.saveDraft).toHaveBeenCalledWith("tenant-service"));
  expect(api.updateEnabledService).toHaveBeenCalledWith("tenant-service", {
    warranty_days: 5, tenant_emergency_surcharge: 0,
  });
  expect(api.updatePricingPolicy).not.toHaveBeenCalled();
});

it("saves the shared fee once without updating individual services", async () => {
  render(<ServicesPricingSetupPage />);
  fireEvent.change(await screen.findByLabelText("Consultation fee"), { target: { value: "399" } });
  fireEvent.click(screen.getByRole("button", { name: "Save fee" }));
  await waitFor(() => expect(api.updatePricingPolicy).toHaveBeenCalledWith({ consultation_fee: 399 }));
  expect(await screen.findByText("Saved for all consultations.")).toBeInTheDocument();
  expect(api.updateEnabledService).not.toHaveBeenCalled();
});

it("keeps invalid shared amounts out of the API", async () => {
  render(<ServicesPricingSetupPage />);
  fireEvent.change(await screen.findByLabelText("Consultation fee"), { target: { value: "0" } });
  fireEvent.click(screen.getByRole("button", { name: "Save fee" }));
  expect(await screen.findByText("Enter a consultation fee greater than zero.")).toBeInTheDocument();
  expect(api.updatePricingPolicy).not.toHaveBeenCalled();
});

it("reports matching-save failures without losing the existing selection", async () => {
  api.setTypes.mockRejectedValue(new Error("offline"));
  render(<ServicesPricingSetupPage />);
  fireEvent.click(await screen.findByRole("checkbox", { name: "Split AC" }));
  expect(await screen.findByText("Could not save the matching selection. Please retry.")).toBeInTheDocument();
  expect(screen.getByRole("checkbox", { name: "Split AC" })).toBeChecked();
});

it("inspection offerings keep visit pricing and matching but no dimension prices", async () => {
  api.listAvailable.mockResolvedValue({ services: [{ ...consultation, job_type: "repair", pricing_model: "inspection_required" }] });
  api.listEnabled.mockResolvedValue({ services: [{ ...enrolled, job_type: "repair", tenant_visit_fee: 249 }] });
  render(<ServicesPricingSetupPage />);
  await screen.findByRole("checkbox", { name: "Split AC" });
  expect(screen.getByText("Inspection charge")).toBeInTheDocument();
  expect(screen.queryByText("Dimension prices")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Save as draft" }));
  await waitFor(() => expect(api.updateEnabledService).toHaveBeenCalledWith("tenant-service", {
    warranty_days: 5, tenant_emergency_surcharge: 0, tenant_visit_fee: 249,
    tenant_min_price: null, tenant_max_price: null,
  }));
});

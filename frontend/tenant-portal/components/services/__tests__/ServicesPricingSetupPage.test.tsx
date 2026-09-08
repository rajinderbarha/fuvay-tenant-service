import React from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  listAvailable: vi.fn(), listEnabled: vi.fn(), getPricingPolicy: vi.fn(),
  updatePricingPolicy: vi.fn(), updateEnabledService: vi.fn(), saveDraft: vi.fn(),
  getAvailableTypes: vi.fn(), getAvailableBrands: vi.fn(), getTypePricing: vi.fn(),
  getBrandPricing: vi.fn(), setTypes: vi.fn(), setBrands: vi.fn(),
  getOverview: vi.fn(), push: vi.fn(),
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: api.push, replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("../../../lib/api", () => ({
  homeServicesSetupApi: api, ServiceOSError: class extends Error {},
  homeServicesSetupOverviewApi: { getOverview: api.getOverview },
}));
vi.mock("../../onboarding/OnboardingShell", () => ({
  OnboardingShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
vi.mock("../ServicesSetupProgress", () => ({ ServicesSetupProgress: () => null }));
vi.mock("../ServiceRequirementsPanel", () => ({ ServiceRequirementsPanel: () => null }));
vi.mock("../InlineDimensionPricingEditor", () => ({
  InlineDimensionPricingEditor: React.forwardRef(() => <div>Dimension prices</div>),
}));
import ServicesPricingSetupPage, { offeringPriceSummary } from "../ServicesPricingSetupPage";

it("formats fixed, range, and inspection pricing according to the Admin workflow", () => {
  expect(offeringPriceSummary(
    { job_type: "service", pricing_model: "fixed" },
    { tenant_min_price: 500, tenant_max_price: 500, tenant_visit_fee: null }, null,
  )).toBe("₹500");
  expect(offeringPriceSummary(
    { job_type: "service", pricing_model: "range" },
    { tenant_min_price: 900, tenant_max_price: 1500, tenant_visit_fee: null }, null,
  )).toBe("₹900–₹1,500");
  expect(offeringPriceSummary(
    { job_type: "repair", pricing_model: "inspection_required" },
    { tenant_min_price: null, tenant_max_price: null, tenant_visit_fee: 249 }, null,
  )).toBe("₹249 inspection");
});

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
  api.getOverview.mockResolvedValue({ progress: { percentage: 40 }, sections: [{ key: "SERVICES_PRICING", status: "complete", blocking_reasons: [] }] });
});

async function openMatching() {
  fireEvent.click(await screen.findByRole("button", { name: /Supported types & brands/ }));
  await screen.findByRole("button", { name: "Split AC" });
}

it("continues after the service step is complete even when overall progress is 40%", async () => {
  render(<ServicesPricingSetupPage />);
  await openMatching();
  fireEvent.click(screen.getByRole("button", { name: "Save & continue" }));
  await waitFor(() => expect(api.push).toHaveBeenCalledWith("/tenant/home-services/setup/plan"));
  expect(api.saveDraft).toHaveBeenCalledWith("tenant-service");
  expect(api.getOverview).toHaveBeenCalledOnce();
});

it("does not continue if another enabled service still needs setup", async () => {
  api.getOverview.mockResolvedValue({ sections: [{ key: "SERVICES_PRICING", status: "not_started", blocking_reasons: [{ message: "Configure the repair inspection fee." }] }] });
  render(<ServicesPricingSetupPage />);
  await openMatching();
  fireEvent.click(screen.getByRole("button", { name: "Save & continue" }));
  expect(await screen.findByText("Configure the repair inspection fee.")).toBeInTheDocument();
  expect(api.push).not.toHaveBeenCalled();
});

it("shows one provider-level fee, with matching controls but no per-consultation amount", async () => {
  render(<ServicesPricingSetupPage />);
  const settings = await screen.findByRole("region", { name: "Provider-wide consultation fee" });
  expect(within(settings).getByLabelText("Consultation fee")).toHaveValue(299);
  expect(screen.getAllByLabelText("Consultation fee")).toHaveLength(1);
  await openMatching();
  fireEvent.click(screen.getByRole("button", { name: "Specific brands" }));
  expect(screen.getByRole("button", { name: "Test brand" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.queryByText("Minimum price")).not.toBeInTheDocument();
  expect(screen.queryByText("Service price")).not.toBeInTheDocument();
  expect(screen.queryByText("Dimension prices")).not.toBeInTheDocument();
  expect(api.getTypePricing).not.toHaveBeenCalled();
  expect(api.getBrandPricing).not.toHaveBeenCalled();
});

it("saves consultation offering settings without a per-service price or visit fee", async () => {
  render(<ServicesPricingSetupPage />);
  await openMatching();
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
  await openMatching();
  fireEvent.click(await screen.findByRole("button", { name: "Split AC" }));
  expect(await screen.findByText("Could not save the matching selection. Please retry.")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Split AC" })).toHaveAttribute("aria-pressed", "true");
});

it("inspection offerings keep visit pricing and matching but no dimension prices", async () => {
  api.listAvailable.mockResolvedValue({ services: [{ ...consultation, job_type: "repair", pricing_model: "inspection_required" }] });
  api.listEnabled.mockResolvedValue({ services: [{ ...enrolled, job_type: "repair", tenant_visit_fee: 249 }] });
  render(<ServicesPricingSetupPage />);
  await screen.findByRole("button", { name: /Supported types & brands/ });
  expect(screen.queryByRole("button", { name: "Split AC" })).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Minimum rough repair estimate")).not.toBeInTheDocument();
  expect(screen.getByRole("switch", { name: /Show customers a rough range/ })).toHaveAttribute("aria-checked", "false");
  await openMatching();
  expect(screen.getByText("Inspection charge")).toBeInTheDocument();
  expect(screen.queryByText("Dimension prices")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Save as draft" }));
  await waitFor(() => expect(api.updateEnabledService).toHaveBeenCalledWith("tenant-service", {
    warranty_days: 5, tenant_emergency_surcharge: 0, tenant_visit_fee: 249,
    tenant_min_price: null, tenant_max_price: null,
  }));
});

it("saves all supported repair brands through matching without changing inspection pricing", async () => {
  api.listAvailable.mockResolvedValue({ services: [{ ...consultation, job_type: "repair", pricing_model: "inspection_required" }] });
  api.listEnabled.mockResolvedValue({ services: [{ ...enrolled, job_type: "repair", tenant_visit_fee: 249 }] });
  const brands = [
    { brand_id: "daikin", name: "Daikin", is_enabled: true },
    { brand_id: "lg", name: "LG", is_enabled: false },
  ];
  api.getAvailableBrands.mockResolvedValue({ brands });
  api.setBrands.mockImplementation(async (_id, ids: string[]) => {
    api.getAvailableBrands.mockResolvedValue({ brands: brands.map(brand => ({ ...brand, is_enabled: ids.includes(brand.brand_id) })) });
  });
  render(<ServicesPricingSetupPage/>);
  await openMatching();
  fireEvent.click(screen.getByRole("button", { name: "All brands" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "All brands" })).toHaveAttribute("aria-pressed", "true"));
  expect(api.setBrands).toHaveBeenCalledWith("tenant-service", ["daikin", "lg"], true);
  expect(api.updateEnabledService).not.toHaveBeenCalled();
  expect(api.getBrandPricing).not.toHaveBeenCalled();
  expect(screen.getByRole("switch", { name: /Show customers a rough range/ })).toHaveAttribute("aria-checked", "false");
});

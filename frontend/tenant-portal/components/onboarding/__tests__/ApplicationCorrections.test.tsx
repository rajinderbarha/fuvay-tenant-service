import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import Overview from "../../../app/(onboarding)/tenant/home-services/setup/overview/page";
import Documents from "../../../app/(onboarding)/tenant/home-services/setup/documents/page";
import { CorrectionActions } from "../CorrectionActions";

const api = vi.hoisted(() => ({ routing: vi.fn(), overview: vi.fn(), status: vi.fn(), requirements: vi.fn(), upload: vi.fn(), push: vi.fn(), replace: vi.fn(), submit: vi.fn() }));
vi.mock("next/navigation", () => {
  const router = { push: api.push, replace: api.replace };
  return { useRouter: () => router };
});
vi.mock("../../../lib/api", () => ({
  ServiceOSError: class extends Error {},
  homeServicesSetupOverviewApi: { getRouting: api.routing, getOverview: api.overview, submitForReview: api.submit },
  tenantDocumentsApi: { getRequirements: api.requirements, submitDocument: api.upload },
  tenantApplicationStatusApi: { get: api.status },
}));
vi.mock("../../../hooks/useTenant", () => ({ useTenant: () => ({ tenantId: "tenant" }) }));
vi.mock("../OnboardingShell", () => ({ OnboardingShell: ({ children }: any) => <div>{children}</div> }));
vi.mock("../VerticalLifecycleBar", () => ({ VerticalLifecycleBar: () => null }));
vi.mock("../SetupOverviewCards", () => ({
  SetupProgressCard: () => <p>Editable setup sections</p>, WorkspaceStatusCard: () => null, OnboardingNextSteps: () => null,
  OnboardingHelpCard: () => null, OnboardingPolicyBanner: () => null, AutosaveStatus: () => null,
}));
vi.mock("../../media/MediaUploader", () => ({ MediaUploader: ({ onUploaded }: any) => <button onClick={() => onUploaded({ id: "gst-media" })}>Test uploaded GST asset</button> }));

beforeEach(() => {
  vi.resetAllMocks();
  api.routing.mockResolvedValue({ next_destination: "HOME_SERVICES_CHANGES_REQUESTED" });
  api.overview.mockResolvedValue({ vertical: { status: "changes_requested", changes_requested_note: "send me gst certificate" }, tenant: { name: "Test" }, sections: [], lifecycle: { stages: [] } });
  api.status.mockResolvedValue({ status: "changes_requested", changes_requested_note: "send me gst certificate" });
  api.requirements.mockResolvedValue({
    business_profile_complete: true, requirements_context: { business_type: "sole_proprietorship", vertical: "home_services" },
    requirements: [{ key: "gst_certificate", label: "GST registration certificate", why: "GST evidence", accepted_examples: ["GST certificate"], required: false, status: "not_uploaded", document: null }],
    additional_documents: [], readiness: { required_total: 3, uploaded: 3, pending_review: 3, rejected: 0, missing: 0, all_required_uploaded: true },
    upload_policy: { allowed_mime_types: ["application/pdf"], max_file_size_mb: 10 },
  });
  api.upload.mockResolvedValue({ id: "gst-document" });
});
afterEach(cleanup);

it("renders the editable overview for corrections instead of redirecting back to status", async () => {
  render(<Overview/>);
  await screen.findByText("Editable setup sections");
  expect(screen.getByText("Changes requested: send me gst certificate")).toBeInTheDocument();
  expect(api.replace).not.toHaveBeenCalled();
  expect(screen.getByRole("link", { name: "Upload or replace documents" })).toHaveAttribute("href", "/tenant/home-services/setup/documents");
});

it.each([
  ["HOME_SERVICES_UNDER_REVIEW", "/onboarding/application-status"],
  ["HOME_SERVICES_ACTIVATION", "/onboarding/activation-center"],
  ["TENANT_DASHBOARD", "/dashboard"],
])("still redirects %s out of the editable overview", async (destination, target) => {
  api.routing.mockResolvedValue({ next_destination: destination });
  render(<Overview/>);
  await waitFor(() => expect(api.replace).toHaveBeenCalledWith(target));
  expect(api.overview).not.toHaveBeenCalled();
});

it.each(["submitted", "under_review", "rejected", "active"])("does not advertise corrections for %s", status => {
  render(<CorrectionActions status={status}/>);
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
});

it("links the GST upload to its canonical document type and offers review without auto-submitting", async () => {
  render(<Documents/>);
  await screen.findByText("send me gst certificate");
  fireEvent.click(screen.getByRole("button", { name: /GST registration certificate/ }));
  fireEvent.click(screen.getByRole("button", { name: "Test uploaded GST asset" }));
  await waitFor(() => expect(api.upload).toHaveBeenCalledWith({ doc_type: "gst_certificate", media_asset_id: "gst-media", label: undefined }));
  await screen.findByText(/Document saved for admin review/);
  fireEvent.click(screen.getByRole("button", { name: "Review & resubmit" }));
  expect(api.push).toHaveBeenCalledWith("/tenant/home-services/setup/review");
  expect(api.submit).not.toHaveBeenCalled();
});

it("preserves the normal documents-next-step flow for initial setup", async () => {
  api.status.mockResolvedValue({ status: "draft_setup" });
  render(<Documents/>);
  const next = await screen.findByRole("button", { name: "Save & continue" });
  fireEvent.click(next);
  expect(api.push).toHaveBeenCalledWith("/tenant/home-services/setup/services-pricing");
  expect(screen.queryByText("Admin requested changes")).not.toBeInTheDocument();
});

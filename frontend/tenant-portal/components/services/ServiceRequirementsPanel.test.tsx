import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
const api = vi.hoisted(() => ({ getServiceRequirements: vi.fn() }));
vi.mock("../../lib/api", () => ({ masterCatalogApi: api, ServiceOSError: class extends Error {} }));
import { ServiceRequirementsPanel } from "./ServiceRequirementsPanel";

const requirements = {
  note: "Platform-managed requirements", problems: [], questions: [],
  checklists: [{ mapping_id: "mapping", template_name: "Before work", version_number: 2,
    purpose: "PRE_WORK", phase: "pre_work", usage: "REQUIRED", actor: "TECHNICIAN",
    completion_gate: "REQUIRE_BEFORE_WORK_START", items: [{ id: "point", label: "Isolate power",
      is_required: true, evidence_required: true, help_text: "Photograph the disconnected supply." }] }],
};
beforeEach(() => { vi.resetAllMocks(); api.getServiceRequirements.mockResolvedValue(requirements); });

it("shows published checklist points and ownership without tenant editing controls", async () => {
  render(<ServiceRequirementsPanel masterServiceId="ac" jobTypeId="installation"/>);
  expect(await screen.findByText("Before work")).toBeInTheDocument();
  expect(api.getServiceRequirements).toHaveBeenCalledWith("ac", "installation");
  expect(screen.getByText("View 1 checklist points")).toBeInTheDocument();
  expect(screen.getByText("Isolate power")).toBeInTheDocument();
  expect(screen.getByText("Photograph the disconnected supply.")).toBeInTheDocument();
  expect(screen.getByText("TECHNICIAN")).toBeInTheDocument();
  expect(screen.queryByRole("textbox")).toBeNull();
  expect(screen.queryByRole("button", { name: /edit|save|publish/i })).toBeNull();
});

it("reloads for a different job type and does not keep the previous checklist", async () => {
  const view = render(<ServiceRequirementsPanel masterServiceId="ac" jobTypeId="installation"/>);
  await screen.findByText("Before work");
  api.getServiceRequirements.mockResolvedValue({ ...requirements, checklists: [] });
  view.rerender(<ServiceRequirementsPanel masterServiceId="ac" jobTypeId="repair"/>);
  await screen.findByText("No problems, questions or checklists have been configured for this service yet.");
  expect(api.getServiceRequirements).toHaveBeenLastCalledWith("ac", "repair");
  expect(screen.queryByText("Before work")).toBeNull();
});

it("shows a load failure instead of treating it as an empty configuration", async () => {
  api.getServiceRequirements.mockRejectedValue(new Error("Network failed"));
  render(<ServiceRequirementsPanel masterServiceId="ac" jobTypeId="repair"/>);
  await waitFor(() => expect(screen.getByText("Requirements for this service could not be loaded.")).toBeInTheDocument());
  expect(screen.queryByText(/No problems, questions or checklists/)).toBeNull();
});

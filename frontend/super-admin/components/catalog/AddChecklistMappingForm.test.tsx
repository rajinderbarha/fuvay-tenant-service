import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
const api = vi.hoisted(() => ({ listPublishedTemplateOptions: vi.fn(), createMapping: vi.fn(), quickCreateMapping: vi.fn() }));
vi.mock("../../lib/api", () => ({ checklistCatalogApi: api, ServiceOSError: class extends Error {} }));
import { AddChecklistMappingForm } from "./AddChecklistMappingForm";

beforeEach(() => { vi.resetAllMocks(); api.listPublishedTemplateOptions.mockResolvedValue([
  { id: "safety", name: "Pre-work safety", purpose: "PRE_WORK", latest_version: { id: "v1", version_number: 1 } },
  { id: "inspection", name: "Inspection", purpose: "INSPECTION", latest_version: { id: "v2", version_number: 2 } },
]); });

it("offers only purpose-compatible gates and maps the exact selected version/job type", async () => {
  api.createMapping.mockResolvedValue({ id: "mapping" });
  const done = vi.fn();
  render(<AddChecklistMappingForm masterServiceJobTypeId="ac-install" onAdded={done} onError={vi.fn()}/>);
  await screen.findByRole("option", { name: "Pre-work safety (v1)" });
  fireEvent.change(screen.getByLabelText("Published checklist"), { target: { value: "v1" } });
  expect(screen.queryByRole("option", { name: "before inspection complete" })).toBeNull();
  fireEvent.change(screen.getByLabelText("Completion gate"), { target: { value: "REQUIRE_BEFORE_WORK_START" } });
  fireEvent.change(screen.getByLabelText("Published checklist"), { target: { value: "v2" } });
  expect((screen.getByLabelText("Completion gate") as HTMLSelectElement).value).toBe("NONE");
  fireEvent.click(screen.getByRole("button", { name: "Map Checklist" }));
  await waitFor(() => expect(done).toHaveBeenCalledOnce());
  expect(api.createMapping).toHaveBeenCalledWith(expect.objectContaining({ master_service_job_type_id: "ac-install", checklist_template_version_id: "v2", completion_gate: "NONE" }));
});

it("creates and maps multiple real points in one request and keeps errors visible for retry", async () => {
  api.quickCreateMapping.mockRejectedValueOnce(new Error("This code already exists")).mockResolvedValueOnce({ mapping: { id: "mapped" } });
  const done = vi.fn();
  render(<AddChecklistMappingForm masterServiceJobTypeId="ac-repair" onAdded={done} onError={vi.fn()}/>);
  fireEvent.click(screen.getByRole("button", { name: "Create new" }));
  fireEvent.change(screen.getByLabelText("Checklist name"), { target: { value: "Safety checks" } });
  expect((screen.getByRole("button", { name: "Create & Map" }) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.change(screen.getByLabelText("Checklist purpose"), { target: { value: "SAFETY" } });
  fireEvent.change(screen.getByLabelText("Checklist points"), { target: { value: " Power off \nGround verified\n" } });
  fireEvent.click(screen.getByRole("button", { name: "Create & Map" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("This code already exists");
  expect(done).not.toHaveBeenCalled();
  expect(api.quickCreateMapping).toHaveBeenCalledWith(expect.objectContaining({ items: ["Power off", "Ground verified"], purpose: "SAFETY", phase: "safety", master_service_job_type_id: "ac-repair" }));
  fireEvent.change(screen.getByLabelText("Checklist code"), { target: { value: "SAFETY_NEW" } });
  fireEvent.click(screen.getByRole("button", { name: "Create & Map" }));
  await waitFor(() => expect(done).toHaveBeenCalledOnce());
  expect(api.createMapping).not.toHaveBeenCalled();
});

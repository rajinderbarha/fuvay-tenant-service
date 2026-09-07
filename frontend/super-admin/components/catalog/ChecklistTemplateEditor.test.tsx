import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
const api = vi.hoisted(() => ({ getLatestVersion: vi.fn(), getOrCreateDraftVersion: vi.fn(), publishVersion: vi.fn(), addSection: vi.fn(), addItem: vi.fn(), updateItem: vi.fn(), deleteItem: vi.fn(), updateSection: vi.fn(), deleteSection: vi.fn() }));
vi.mock("../../lib/api", () => ({ checklistCatalogApi: api, ServiceOSError: class extends Error {} }));
import { ChecklistTemplateEditor } from "./ChecklistTemplateEditor";
import { ChecklistItemEditor } from "./ChecklistItemEditor";
const version = { id: "v1", version_number: 1, status: "DRAFT", sections: [{ id: "s1", title: "Before work", items: [{ id: "i1", label: "Power off", item_type: "CHECKBOX", is_required: true }] }] };
beforeEach(() => { vi.resetAllMocks(); api.getLatestVersion.mockResolvedValue(version); });

it("refreshes published content immediately and removes stale draft actions", async () => {
  api.publishVersion.mockImplementation(async () => { api.getLatestVersion.mockResolvedValue({ ...version, status: "PUBLISHED" }); return {}; });
  render(<ChecklistTemplateEditor templateId="template"/>);
  fireEvent.click(await screen.findByRole("button", { name: "Publish version" }));
  await screen.findByRole("button", { name: "Create editable draft" });
  expect(screen.queryByRole("button", { name: "Publish version" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Edit item" })).toBeNull();
  expect(api.publishVersion).toHaveBeenCalledWith("v1", undefined);
});

it("does not publish an empty draft and shows section save errors", async () => {
  api.getLatestVersion.mockResolvedValue({ ...version, sections: [] });
  api.addSection.mockRejectedValue(new Error("Section title is invalid"));
  render(<ChecklistTemplateEditor templateId="empty"/>);
  expect((await screen.findByRole("button", { name: "Publish version" }) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.change(screen.getByLabelText("New section title"), { target: { value: "Before work" } });
  fireEvent.click(screen.getByRole("button", { name: "Add section" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Section title is invalid");
});

it("requires real select choices and hides incompatible evidence controls", async () => {
  api.addItem.mockResolvedValue({ id: "new-item" });
  const saved = vi.fn();
  render(<ChecklistItemEditor sectionId="s1" onSaved={saved}/>);
  fireEvent.click(screen.getByRole("button", { name: "+ Add item" }));
  expect(screen.queryByText("Require uploaded evidence")).toBeNull();
  fireEvent.change(screen.getByLabelText("Item label"), { target: { value: "Condition" } });
  fireEvent.change(screen.getByLabelText("Answer type"), { target: { value: "SINGLE_SELECT" } });
  expect((screen.getByRole("button", { name: "Save item" }) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.change(screen.getByLabelText("Choices"), { target: { value: "Good\nNeeds repair" } });
  fireEvent.click(screen.getByRole("button", { name: "Save item" }));
  await waitFor(() => expect(saved).toHaveBeenCalledOnce());
  expect(api.addItem).toHaveBeenCalledWith("s1", expect.objectContaining({ select_options: [{ value: "Good", label: "Good" }, { value: "Needs repair", label: "Needs repair" }], evidence_required: false, is_required: true }));
});

import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
const api = vi.hoisted(() => ({ getWorkflowStepOptions: vi.fn(), reviewWorkflowSteps: vi.fn(), setJobTypeWorkflow: vi.fn() }));
vi.mock("../../../lib/api", () => ({ catalogWorkspaceApi: api, ServiceOSError: class extends Error {} }));
import { WorkflowStepBuilder } from "./WorkflowStepBuilder";
import type { ServiceJobWorkflow } from "../../../lib/api";

const props = { masterServiceId: "service", jobTypeId: "repair", canWrite: true, notify: vi.fn(), onSaved: vi.fn() };
beforeEach(() => {
  vi.clearAllMocks();
  api.getWorkflowStepOptions.mockResolvedValue({ job_statuses: ["assigned", "on_the_way"], owner_apps: ["staff_app"], owner_roles: ["technician"] });
  api.reviewWorkflowSteps.mockResolvedValue({ valid: true, errors: [], warnings: [] });
  api.setJobTypeWorkflow.mockResolvedValue({});
});
function workflow(steps: unknown[] = []) { return { version_number: 1, steps, transitions: [] } as unknown as ServiceJobWorkflow; }

it("makes custom journey optional without publishing any change automatically", async () => {
  render(<WorkflowStepBuilder {...props} workflow={workflow()} />);
  expect(screen.getByText("Cross-app journey · Optional")).toBeInTheDocument();
  expect(screen.getByText(/No extra setup is required here/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Publish journey version" })).toBeDisabled();
  expect(api.setJobTypeWorkflow).not.toHaveBeenCalled();
});

it("switches to standard only when the admin explicitly publishes the change", async () => {
  render(<WorkflowStepBuilder {...props} workflow={workflow([{ step_key: "assigned", step_name: "Assigned", maps_to_status: "assigned", owner_app: "staff_app", owner_role: "technician" }])} />);
  fireEvent.click(screen.getByRole("button", { name: "Use standard journey" }));
  expect(api.setJobTypeWorkflow).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Publish journey version" }));
  await waitFor(() => expect(api.setJobTypeWorkflow).toHaveBeenCalledWith("service", "repair", { steps: [], transitions: [] }));
});

it("keeps stable distinct keys for steps with similar names", async () => {
  render(<WorkflowStepBuilder {...props} workflow={workflow()} />);
  const add = screen.getByRole("button", { name: "Add step" });
  await waitFor(() => expect(add).toBeEnabled());
  fireEvent.click(add);
  fireEvent.click(add);
  const names = screen.getAllByLabelText("Step name");
  fireEvent.change(names[0], { target: { value: "Technician assigned" } });
  fireEvent.change(names[1], { target: { value: "Technician travelling" } });
  fireEvent.click(screen.getByRole("button", { name: "Publish journey version" }));
  await waitFor(() => expect(api.setJobTypeWorkflow).toHaveBeenCalledOnce());
  const saved = api.setJobTypeWorkflow.mock.calls[0][2].steps;
  expect(saved[0].step_key).not.toBe(saved[1].step_key);
  expect(saved[0].step_name).toBe("Technician assigned");
});

it("shows server review errors rather than a misleading success badge", async () => {
  api.reviewWorkflowSteps.mockResolvedValue({ valid: false, errors: ["This transition can never fire."], warnings: [] });
  render(<WorkflowStepBuilder {...props} workflow={workflow()} />);
  expect(await screen.findByText("This transition can never fire.")).toBeInTheDocument();
});

import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
const api = vi.hoisted(() => ({ listJobTypes: vi.fn(), addServiceJobType: vi.fn() }));
vi.mock("../../lib/api", () => ({ catalogWorkspaceApi: api, ServiceOSError: class extends Error {} }));
import { AddServiceJobType } from "./AddServiceJobType";
it("only attaches active runtime-supported choices without creating platform types", async () => {
  api.listJobTypes.mockResolvedValue({ items: [
    { id: "install", label: "Installation", is_active: true, runtime_supported: true },
    { id: "repair", label: "Repair", is_active: true, runtime_supported: true },
    { id: "odd", label: "Unsupported", is_active: true, runtime_supported: false },
    { id: "old", label: "Inactive", is_active: false, runtime_supported: true },
  ] });
  api.addServiceJobType.mockResolvedValue({ id: "link" });
  const onAdded = vi.fn();
  render(<AddServiceJobType masterServiceId="ac" linkedJobTypeIds={["repair"]} onAdded={onAdded} onError={vi.fn()} />);
  await screen.findByRole("option", { name: "Installation" });
  expect(screen.queryByRole("option", { name: "Repair" })).toBeNull();
  expect(screen.queryByRole("option", { name: "Unsupported" })).toBeNull();
  expect(screen.queryByRole("option", { name: "Inactive" })).toBeNull();
  expect(screen.queryByText("Define new")).toBeNull();
  fireEvent.change(screen.getByLabelText("Job type"), { target: { value: "install" } });
  fireEvent.click(screen.getByRole("button", { name: "Add job type" }));
  await waitFor(() => expect(onAdded).toHaveBeenCalledOnce());
  expect(api.addServiceJobType).toHaveBeenCalledWith("ac", "install");
});

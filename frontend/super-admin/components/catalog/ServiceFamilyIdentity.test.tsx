import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
const update = vi.hoisted(() => vi.fn());
vi.mock("../../lib/api", () => ({ catalogApi: { updateMasterService: update }, ServiceOSError: class extends Error {} }));
import { ServiceFamilyIdentity } from "./ServiceFamilyIdentity";
it("requires an explicit name save and sends no job-type or pricing mutations", async () => {
  update.mockResolvedValue({});
  const onSaved = vi.fn();
  render(<ServiceFamilyIdentity serviceId="ac" name="AC Installation" canWrite onSaved={onSaved} />);
  expect(update).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Edit family name" }));
  fireEvent.change(screen.getByLabelText("Service family name"), { target: { value: "Air Conditioner" } });
  fireEvent.click(screen.getByRole("button", { name: "Save family name" }));
  await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
  expect(update).toHaveBeenCalledWith("ac", { service_name: "Air Conditioner" });
});
it("does not offer writes to read-only admins", () => {
  render(<ServiceFamilyIdentity serviceId="ac" name="AC Repair" canWrite={false} onSaved={vi.fn()} />);
  expect(screen.queryByRole("button", { name: "Edit family name" })).toBeNull();
});

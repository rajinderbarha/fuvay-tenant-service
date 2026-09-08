import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AddTeamMemberWizard } from "../AddTeamMemberWizard";
import { TeamLoginCredentials } from "../TeamLoginCredentials";

const api = vi.hoisted(() => ({
  create: vi.fn(), update: vi.fn(), generatePassword: vi.fn(), activate: vi.fn(), deactivate: vi.fn(),
  skills: vi.fn(), services: vi.fn(),
}));
vi.mock("../../../lib/api", () => ({
  getTenantId: () => "tenant", ServiceOSError: class extends Error {},
  providerTeamMembersApi: api,
  providerTeamSkillsApi: { list: api.skills },
  homeServicesSetupApi: { listEnabled: api.services },
}));
vi.mock("../../shared/ProfilePhotoUploader", () => ({ ProfilePhotoUploader: () => null }));
const credentials = { member_id: "member", user_id: "user", username: "team@example.test", temporary_password: "Test-Only-Pass42!", force_password_change: true, access_active: true };
const member = { member_id: "member", full_name: "Team Member", email: "team@example.test", member_type: "staff", status: "active", user_id: "user" } as any;

beforeEach(() => {
  cleanup(); vi.clearAllMocks();
  api.skills.mockResolvedValue({ skills: [] });
  api.services.mockResolvedValue({ services: [] });
  api.generatePassword.mockResolvedValue(credentials);
  api.deactivate.mockResolvedValue({ ...member, status: "inactive" });
  api.activate.mockResolvedValue(member);
  vi.spyOn(window, "confirm").mockReturnValue(true);
});

describe("Provider-managed team login", () => {
  it("creates the member before generating credentials and does not close over the result", async () => {
    api.create.mockResolvedValue({ member: { ...member, user_id: null } });
    const onSaved = vi.fn();
    render(<AddTeamMemberWizard existing={null} technicianSeatAvailable={false} onClose={vi.fn()} onSaved={onSaved}/>);
    fireEvent.change(screen.getByPlaceholderText("Enter full name"), { target: { value: "New Member" } });
    fireEvent.change(screen.getByPlaceholderText("name@business.com"), { target: { value: "team@example.test" } });
    fireEvent.click(screen.getByRole("button", { name: "Login access" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "Generate login password so this member can use the app" }));
    fireEvent.click(screen.getByRole("button", { name: "Add team member" }));
    await screen.findByLabelText("Login credentials");
    expect(api.create).toHaveBeenCalledOnce();
    expect(api.generatePassword).toHaveBeenCalledWith("member");
    expect(api.create.mock.invocationCallOrder[0]).toBeLessThan(api.generatePassword.mock.invocationCallOrder[0]);
    expect(onSaved).not.toHaveBeenCalled();
  });

  it("regenerates an existing password without saving unrelated profile edits and keeps credentials visible", async () => {
    const onSaved = vi.fn();
    render(<AddTeamMemberWizard existing={member} initialSection={4} onClose={vi.fn()} onSaved={onSaved}/>);
    fireEvent.click(screen.getByRole("button", { name: "Regenerate temporary password" }));
    expect(await screen.findByRole("region", { name: "Generated login credentials" })).toBeTruthy();
    expect(api.generatePassword).toHaveBeenCalledWith("member");
    expect(api.update).not.toHaveBeenCalled();
    expect(onSaved).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Done" }));
    expect(onSaved).toHaveBeenCalledOnce();
  });

  it("disables the member and prevents generating credentials until enabled", async () => {
    render(<AddTeamMemberWizard existing={member} initialSection={4} onClose={vi.fn()} onSaved={vi.fn()}/>);
    fireEvent.click(screen.getByRole("button", { name: "Disable member" }));
    await screen.findByRole("button", { name: "Enable member" });
    expect(api.deactivate).toHaveBeenCalledWith("member");
    expect((screen.getByRole("button", { name: "Regenerate temporary password" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Enable member" }));
    await screen.findByRole("button", { name: "Disable member" });
    expect(api.activate).toHaveBeenCalledWith("member");
  });

  it("does not report success or lose the retry action when generation fails", async () => {
    api.generatePassword.mockRejectedValue(new Error("failure"));
    render(<AddTeamMemberWizard existing={member} initialSection={4} onClose={vi.fn()} onSaved={vi.fn()}/>);
    fireEvent.click(screen.getByRole("button", { name: "Regenerate temporary password" }));
    await screen.findByText("Could not generate login credentials. Try again.");
    expect(screen.queryByLabelText("Login credentials")).toBeNull();
    expect((screen.getByRole("button", { name: "Regenerate temporary password" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("loads enabled services independently when optional skills fail", async () => {
    api.skills.mockRejectedValue(new Error("skills unavailable"));
    api.services.mockResolvedValue({ services: [{ tenant_service_id: "offering", master_service_id: "service", service_name: "Air Conditioner", job_type: "repair", is_enabled: true }] });
    render(<AddTeamMemberWizard existing={{ ...member, member_type: "technician" }} initialSection={3} onClose={vi.fn()} onSaved={vi.fn()}/>);
    expect(await screen.findByText("Air Conditioner")).toBeTruthy();
    expect(screen.queryByText(/Enabled services could not be loaded/)).toBeNull();
  });

  it("supports manual copying on HTTP where the Clipboard API is unavailable", async () => {
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: undefined });
    render(<TeamLoginCredentials credentials={credentials}/>);
    fireEvent.click(screen.getByRole("button", { name: "Copy credentials" }));
    await waitFor(() => expect(screen.getByRole("status").textContent).toContain("Ctrl+C"));
    expect(document.activeElement).toBe(screen.getByLabelText("Login credentials"));
  });
});

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React, { useState } from "react";
import { Modal } from "../components/Modal";

describe("Modal", () => {
  it("traps focus inside the dialog and closes on Escape", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(
      <Modal open onClose={onClose} title="Confirm" footer={<button>Confirm</button>}>
        <button>Body button</button>
      </Modal>
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("renders nothing when closed", () => {
    render(
      <Modal open={false} onClose={() => {}} title="Confirm">
        body
      </Modal>
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("keeps focus in a controlled field when an inline close callback changes", async () => {
    const user = userEvent.setup();

    function ControlledReasonModal() {
      const [reason, setReason] = useState("");
      return (
        <Modal open onClose={() => undefined} title="Reassign technician">
          <label>
            Reason
            <textarea
              aria-label="Reason"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
          </label>
        </Modal>
      );
    }

    render(<ControlledReasonModal />);
    const reason = screen.getByRole("textbox", { name: "Reason" });
    await user.click(reason);
    await user.type(reason, "Needs another technician");

    expect(reason).toHaveValue("Needs another technician");
    expect(reason).toHaveFocus();
  });

  it("honours a form field marked for initial focus instead of the close button", () => {
    render(
      <Modal open onClose={() => undefined} title="Reason required">
        <textarea aria-label="Operational reason" autoFocus />
      </Modal>,
    );

    expect(screen.getByRole("textbox", { name: "Operational reason" })).toHaveFocus();
  });
});

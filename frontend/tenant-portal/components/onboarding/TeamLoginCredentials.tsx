"use client";

import { useRef, useState } from "react";
import { Btn } from "../shared/ui";
import type { TeamMemberLoginCredentials } from "../../lib/api";

/** Kept only in component memory; never localStorage, notifications or URLs. */
export function TeamLoginCredentials({ credentials }: { credentials: TeamMemberLoginCredentials }) {
  const field = useRef<HTMLTextAreaElement>(null);
  const [message, setMessage] = useState("");
  const loginUrl = typeof window === "undefined" ? "/staff/login" : `${window.location.origin}/staff/login`;
  const text = `Login page: ${loginUrl}\nLogin email: ${credentials.username}\nTemporary password: ${credentials.temporary_password}`;
  async function copy() {
    try {
      if (!navigator.clipboard) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(text);
      setMessage("Copied. Share privately with this team member.");
    } catch {
      field.current?.focus();
      field.current?.select();
      setMessage("Credentials selected. Press Ctrl+C (or copy manually) to copy.");
    }
  }
  return <section aria-label="Generated login credentials" style={{ padding: 16, marginTop: 16, border: "1px solid var(--border)", borderRadius: 12, background: "var(--surface-sunken)" }}>
    <strong>Copy this password now</strong>
    <p style={{ fontSize: 12 }}>Share these credentials privately. The password is shown only once, and must be changed at first login. Any previous password and sessions have been replaced.</p>
    <textarea ref={field} aria-label="Login credentials" readOnly value={text} rows={4} spellCheck={false}
      style={{ width: "100%", boxSizing: "border-box", resize: "none", padding: 12, borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)" }}/>
    <Btn variant="secondary" onClick={copy}>Copy credentials</Btn>
    {message && <p role="status" style={{ fontSize: 12 }}>{message}</p>}
  </section>;
}

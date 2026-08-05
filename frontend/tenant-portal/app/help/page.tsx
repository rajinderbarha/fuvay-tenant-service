"use client";
/**
 * Help & Support (onboarding-scoped). Previously a dead link -- every
 * "Help & Support" link in OnboardingShell pointed at /help, which had no
 * page.tsx at all, so Next.js 404'd.
 *
 * Correction (2026-08-04): this page used to say "a dedicated support
 * contact channel isn't set up yet" -- that became false the moment the
 * real support-ticket engine (app.engines.support, /v1/tenant/support/*)
 * was built and wired to the full /help-support workspace page. Rather than
 * send a still-onboarding tenant into that page's full dashboard chrome
 * (Bookings/Schedule/Customers/etc., all meaningless pre-activation), this
 * embeds a minimal real "Create support request" form using the same
 * `supportApi.createRequest` the full workspace uses, inside the
 * restricted OnboardingShell.
 */
import { useEffect, useState } from "react";
import Link from "next/link";
import { HelpCircle, MessageSquare, FileText, Rocket, CheckCircle2, AlertTriangle } from "lucide-react";
import { OnboardingShell } from "../../components/onboarding/OnboardingShell";
import { Card, Select, Input, Btn } from "../../components/shared/ui";
import { supportApi, ServiceOSError, type SupportWorkspace } from "../../lib/api";

function CreateRequestCard() {
  const [ws, setWs] = useState<SupportWorkspace | null>(null);
  const [category, setCategory] = useState("");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [impact, setImpact] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<{ ticket_number: string } | null>(null);

  useEffect(() => {
    supportApi.workspace().then(setWs).catch(() => setWs(null));
  }, []);

  const canSubmit = !!category && subject.trim().length >= 3 && description.trim().length >= 10 && !!impact;

  async function submit() {
    setBusy(true); setError(null);
    try {
      const d = await supportApi.createRequest({ category, subject, description, impact });
      setCreated({ ticket_number: d.ticket_number ?? d.ticket_id ?? "submitted" });
    } catch (e) {
      setError(e instanceof ServiceOSError ? e.message : "Could not submit your request. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  if (created) {
    return (
      <Card>
        <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
          <CheckCircle2 size={18} style={{ color: "var(--success)", flexShrink: 0, marginTop: 2 }}/>
          <div>
            <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>Request submitted — {created.ticket_number}</p>
            <p style={{ fontSize: 12.5, color: "var(--text-secondary)", margin: 0 }}>Our support team will follow up. You can track replies from your full workspace&apos;s Help &amp; Support once activated.</p>
          </div>
        </div>
      </Card>
    );
  }

  if (ws === null) return null; // fails quiet -- Messages & Requests card above still covers reviewer contact

  return (
    <Card style={{ marginBottom: 16 }}>
      <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>Create a support request</p>
      <p style={{ fontSize: 12.5, color: "var(--text-secondary)", margin: "0 0 14px" }}>For anything not covered by Messages &amp; Requests below.</p>
      <div style={{ display: "grid", gap: 12 }}>
        <Select label="Category" value={category} onChange={setCategory} placeholder="Choose the area this is about"
          options={(ws.form_options?.categories ?? []).map((c: { key: string; label: string }) => ({ value: c.key, label: c.label }))}/>
        <Select label="Impact on your business" value={impact} onChange={setImpact} placeholder="How urgent is this?"
          options={(ws.form_options?.impacts ?? []).map((i: { key: string; label: string }) => ({ value: i.key, label: i.label }))}/>
        <Input label="Subject" value={subject} onChange={setSubject} placeholder="Short summary"/>
        <Input label="Description" value={description} onChange={setDescription} rows={4}
          placeholder="What happened, and what were you trying to do?"/>
        {error && (
          <div role="alert" style={{ display: "flex", gap: 8, fontSize: 12.5, color: "var(--danger-text)" }}>
            <AlertTriangle size={14} style={{ flexShrink: 0, marginTop: 1 }}/><span>{error}</span>
          </div>
        )}
        <Btn variant="primary" disabled={!canSubmit || busy} onClick={submit}>
          {busy ? "Submitting…" : "Submit request"}
        </Btn>
      </div>
    </Card>
  );
}

export default function HelpPage() {
  return (
    <OnboardingShell activeNav="help" restricted>
      <div style={{ marginBottom: 20 }}>
        <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", color: "var(--brand)", margin: "0 0 6px" }}>ONBOARDING</p>
        <h1 style={{ fontSize: 26, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 6px" }}>Help &amp; support</h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>Answers and contact options while your Home Services setup is reviewed.</p>
      </div>

      <CreateRequestCard/>

      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: "var(--surface-sunken)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, color: "var(--text-tertiary)" }}>
            <MessageSquare size={18}/>
          </div>
          <div>
            <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>Reviewer feedback and requests</p>
            <p style={{ fontSize: 12.5, color: "var(--text-secondary)", margin: "0 0 10px" }}>If Admin has asked for changes or left a decision note, it appears in Messages &amp; Requests.</p>
            <Link href="/onboarding/messages" style={{ fontSize: 12.5, fontWeight: 600, color: "var(--brand)", textDecoration: "none" }}>Go to Messages &amp; Requests →</Link>
          </div>
        </div>
      </Card>

      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: "var(--surface-sunken)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, color: "var(--text-tertiary)" }}>
            <FileText size={18}/>
          </div>
          <div>
            <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>Where things stand</p>
            <p style={{ fontSize: 12.5, color: "var(--text-secondary)", margin: "0 0 10px" }}>Submission status, version and review timeline live on Application Status. Your locked, submitted answers are on Submitted Setup.</p>
            <div style={{ display: "flex", gap: 16 }}>
              <Link href="/onboarding/application-status" style={{ fontSize: 12.5, fontWeight: 600, color: "var(--brand)", textDecoration: "none" }}>Application Status →</Link>
              <Link href="/onboarding/submitted-setup" style={{ fontSize: 12.5, fontWeight: 600, color: "var(--brand)", textDecoration: "none" }}>Submitted Setup →</Link>
            </div>
          </div>
        </div>
      </Card>

      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: "var(--surface-sunken)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, color: "var(--text-tertiary)" }}>
            <Rocket size={18}/>
          </div>
          <div>
            <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>Activation requirements</p>
            <p style={{ fontSize: 12.5, color: "var(--text-secondary)", margin: "0 0 10px" }}>Once approved, any remaining steps before your workspace goes live are tracked on the Activation Center.</p>
            <Link href="/onboarding/activation-center" style={{ fontSize: 12.5, fontWeight: 600, color: "var(--brand)", textDecoration: "none" }}>Activation Center →</Link>
          </div>
        </div>
      </Card>

      <Card>
        <div style={{ display: "flex", gap: 10, padding: "2px 0" }}>
          <HelpCircle size={16} style={{ color: "var(--text-tertiary)", flexShrink: 0, marginTop: 1 }}/>
          <p style={{ fontSize: 12.5, color: "var(--text-tertiary)", margin: 0, lineHeight: 1.6 }}>
            Use the form above for anything support-related, or Messages &amp; Requests for reviewer
            feedback specific to your submission.
          </p>
        </div>
      </Card>
    </OnboardingShell>
  );
}

"use client";
/**
 * Tenant Onboarding — Staff & Technicians (step 6 of 8).
 * Roster + readiness/coverage are entirely backend-derived
 * (providerTeamMembersApi.readiness/coverage) — this page never computes
 * readiness itself. Add/Edit opens a dedicated multistep wizard (not a
 * long single modal): Identity -> Role & Access -> Services & Skills ->
 * Availability -> Review.
 */
import React, { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  UserPlus, Search, CheckCircle2, AlertTriangle,
  ShieldOff, XCircle, ChevronRight,
} from "lucide-react";
import { OnboardingShell } from "../../../../../../components/onboarding/OnboardingShell";
import { Card, Btn, Badge, Skeleton } from "../../../../../../components/shared/ui";
import { ActionMenu } from "../../../../../../components/shared/layout";
import {
  providerTeamMembersApi, ServiceOSError,
  type ProviderTeamMember, type TeamReadinessSummary, type ServiceCoverageRow,
} from "../../../../../../lib/api";
import { topupApi } from "../../../../../../lib/api-topup";
import { AddTeamMemberWizard } from "../../../../../../components/onboarding/AddTeamMemberWizard";

const READINESS_META: Record<string, { label: string; variant: "default" | "success" | "warning" | "danger" | "info"; icon: React.ReactNode }> = {
  ready:                     { label: "Ready",               variant: "success", icon: <CheckCircle2 size={13}/> },
  needs_identity:            { label: "Needs identity",       variant: "warning", icon: <AlertTriangle size={13}/> },
  needs_role:                { label: "Needs role",           variant: "warning", icon: <AlertTriangle size={13}/> },
  needs_service_assignment:  { label: "Needs setup",          variant: "warning", icon: <AlertTriangle size={13}/> },
  needs_availability:        { label: "Needs setup",          variant: "warning", icon: <AlertTriangle size={13}/> },
  invitation_pending:        { label: "Invitation pending",   variant: "info",    icon: <AlertTriangle size={13}/> },
  access_disabled:           { label: "Access disabled",      variant: "danger",  icon: <ShieldOff size={13}/> },
  offboarded:                { label: "Inactive",             variant: "default", icon: <XCircle size={13}/> },
};

export default function StaffTechniciansPage() {
  const router = useRouter();
  const [members, setMembers] = useState<ProviderTeamMember[]>([]);
  const [readiness, setReadiness] = useState<TeamReadinessSummary | null>(null);
  const [coverage, setCoverage] = useState<ServiceCoverageRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const [wizardOpen, setWizardOpen] = useState(false);
  const [editingMember, setEditingMember] = useState<ProviderTeamMember | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    Promise.all([
      providerTeamMembersApi.list(),
      providerTeamMembersApi.readiness(),
      providerTeamMembersApi.coverage(),
    ])
      .then(([m, r, c]) => { setMembers(m.members); setReadiness(r); setCoverage(c.coverage); })
      .catch(e => setError(e instanceof ServiceOSError ? e.message : "We couldn't load your team."))
      .finally(() => setLoading(false));
  }, []);

  // Same gate as the Team workspace, so onboarding cannot quietly add
  // technicians the plan does not pay for and then fail at the API.
  const [seats, setSeats] = useState<{ entitled: number; available: number; credit: number } | null>(null);
  useEffect(() => {
    topupApi.status()
      .then(s => setSeats({
        entitled: s.entitled_seats ?? 0,
        available: s.available_seats ?? 0,
        credit: s.credit_balance ?? 0,
      }))
      .catch(() => setSeats(null));  // never block setup on a finance read
  }, []);
  const noPlan = seats?.entitled === 0;
  const seatsFull = !!seats && !noPlan && seats.available <= 0;
  const creditOut = !!seats && seats.credit <= 0;

  useEffect(() => { load(); }, [load]);

  async function handleDeactivate(id: string) {
    if (!confirm("Disable access for this team member? They will no longer be able to sign in or receive new assignments.")) return;
    try { await providerTeamMembersApi.deactivate(id); load(); }
    catch (e) { setError(e instanceof ServiceOSError ? e.message : "Could not disable access."); }
  }
  async function handleActivate(id: string) {
    try { await providerTeamMembersApi.activate(id); load(); }
    catch (e) { setError(e instanceof ServiceOSError ? e.message : "Could not restore access."); }
  }
  async function handleSendInvite(member: ProviderTeamMember) {
    if (!member.email) {
      setEditingMember(member);
      setWizardOpen(true);
      return;
    }
    try {
      const result = await providerTeamMembersApi.createLogin(member.member_id);
      if (result.activation_token && !result.activation_sent) {
        await navigator.clipboard?.writeText(result.activation_token);
      }
      setNotice(result.access_active
        ? "App access is already active."
        : result.activation_sent
          ? `App invitation sent to ${member.email}.`
          : result.activation_token
            ? "Development activation code copied to the clipboard."
            : "Invitation created, but email delivery could not be confirmed.");
      load();
    } catch (e) {
      setError(e instanceof ServiceOSError ? e.message : "Could not send the app invitation.");
    }
  }

  const filtered = members.filter(m => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return m.full_name.toLowerCase().includes(q)
      || (m.email || "").toLowerCase().includes(q)
      || (m.phone || "").includes(q)
      || (m.member_type || "").toLowerCase().includes(q)
      || (m.designation || "").toLowerCase().includes(q)
      || (m.skills || []).some(skill => skill.toLowerCase().includes(q));
  });

  if (loading) {
    return (
      <OnboardingShell activeNav="staff">
        <Skeleton height={60} style={{ marginBottom: 16 }}/>
        <Skeleton height={320} style={{ marginBottom: 16 }}/>
        <Skeleton height={200}/>
      </OnboardingShell>
    );
  }

  const counts = readiness?.counts;
  const statusLine = !counts ? "" : counts.total === 0 ? "Optional for now" : `${counts.ready} of ${counts.total} ready`;
  const coverageGaps = coverage.filter(c => c.ready_technician_count === 0);

  return (
    <OnboardingShell activeNav="staff">
      <style>{`
        .staff-grid { display: grid; grid-template-columns: minmax(0,1fr) 300px; gap: 24px; align-items: start; }
        .staff-row { display: flex; align-items: center; gap: 12px; padding: 12px 16px; }
        @media (max-width: 900px) { .staff-grid { grid-template-columns: 1fr; } }
        @media (max-width: 700px) { .staff-row { flex-wrap: wrap; } }
      `}</style>

      {error && (
        <div role="alert" style={{ display: "flex", gap: 8, padding: "12px 14px", borderRadius: 10, background: "var(--danger-bg)", border: "1px solid var(--danger-border)", color: "var(--danger-text)", fontSize: 13, marginBottom: 16 }}>
          <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 1 }}/><span>{error}</span>
        </div>
      )}
      {notice && (
        <div role="status" style={{ padding: "11px 14px", borderRadius: 10, background: "var(--success-bg)", border: "1px solid var(--success-border)", color: "var(--success-text)", fontSize: 13, marginBottom: 16 }}>
          {notice}
        </div>
      )}

      {/* Locked, not hidden: onboarding must still show what a plan unlocks and
          how to buy one, otherwise this step becomes a dead end. */}
      {(noPlan || seatsFull || creditOut) && (
        <div role="status" style={{ display: "flex", gap: 8, padding: "12px 14px", borderRadius: 10, background: "var(--warning-bg)", border: "1px solid var(--warning-border)", color: "var(--warning-text)", fontSize: 13, marginBottom: 16 }}>
          <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 1 }}/>
          <span>
            {noPlan
              ? <><strong>Buy a top-up plan to add technicians.</strong> A plan grants the technician seats that decide how many jobs you can run in one slot.</>
              : seatsFull
              ? <>All {seats?.entitled} purchased seat{seats?.entitled === 1 ? "" : "s"} are in use. Buy another plan to add more technicians.</>
              : <><strong>Your team is suspended — the workspace is out of credit.</strong> Technicians cannot be activated or assigned work until you top up.</>}
            {" "}<Link href="/home-services/finance">Open finance</Link>
          </span>
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12, marginBottom: 6 }}>
        <div>
          <p style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.06em", color: "var(--brand)", margin: "0 0 6px", textTransform: "uppercase" }}>Tenant Onboarding</p>
          <h1 style={{ fontSize: 26, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 6px" }}>Staff &amp; technicians</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>Add your team and assign the services they can perform.</p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {counts && <Badge variant={counts.total === 0 ? "info" : counts.ready === counts.total ? "success" : "warning"}>{statusLine}</Badge>}
          <Btn variant="primary" disabled={noPlan || seatsFull}
               onClick={() => { setEditingMember(null); setWizardOpen(true); }}>
            <UserPlus size={15}/> Add team member
          </Btn>
        </div>
      </div>
      <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "8px 0 24px" }}>Step 6 of 8</p>

      <div className="staff-grid">
        <div>
          <Card>
            <p style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 16px" }}>Team roster</p>
            <div style={{ position: "relative", marginBottom: 16 }}>
              <Search size={15} style={{ position: "absolute", left: 12, top: 13, color: "var(--text-tertiary)" }}/>
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search by name, role or service"
                style={{ width: "100%", height: 40, padding: "0 12px 0 36px", fontSize: 13, borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)", boxSizing: "border-box", fontFamily: "inherit" }}/>
            </div>

            {filtered.length === 0 && (
              <div style={{ textAlign: "center", padding: "40px 20px" }}>
                <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 16px" }}>
                  {members.length === 0 ? "No team members added yet." : "No team members match your search."}
                </p>
                {members.length === 0 && (
                  <Btn variant="primary" onClick={() => { setEditingMember(null); setWizardOpen(true); }}>
                    <UserPlus size={15}/> Add your first team member
                  </Btn>
                )}
              </div>
            )}

            <div style={{ border: filtered.length ? "1px solid var(--border)" : "none", borderRadius: 10, overflow: "visible", position: "relative" }}>
              {filtered.map((m, i) => {
                const r = readiness?.per_member[m.member_id];
                const meta = READINESS_META[r?.status ?? "needs_identity"];
                return (
                  <div key={m.member_id} className="staff-row" style={{ borderBottom: i === filtered.length - 1 ? "none" : "1px solid var(--border)", background: "var(--surface)" }}>
                    <div style={{ width: 36, height: 36, borderRadius: "50%", background: "var(--surface-sunken)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, fontSize: 13, fontWeight: 700, color: "var(--text-secondary)", overflow: "hidden" }}>
                      {m.profile_photo_url ? <img src={m.profile_photo_url} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }}/> : m.full_name.slice(0, 2).toUpperCase()}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 2px" }}>{m.full_name}</p>
                      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>{m.email || m.phone || "No contact"}</p>
                    </div>
                    <Badge size="sm">{m.member_type}</Badge>
                    <Badge variant={meta.variant} size="sm">{meta.icon} {meta.label}</Badge>
                    <button onClick={() => { setEditingMember(m); setWizardOpen(true); }} style={{
                      fontSize: 12, fontWeight: 600, color: "var(--brand)", background: "none", border: "none", cursor: "pointer",
                    }}>View setup</button>
                    <ActionMenu
                      size="xs"
                      items={[
                        !m.login_active && {
                          label: m.email
                            ? (m.password_generated ? "Resend app invitation" : "Send app invitation")
                            : "Add email to send invitation",
                          onClick: () => handleSendInvite(m),
                        },
                        m.status === "active"
                          ? { label: "Disable access", onClick: () => handleDeactivate(m.member_id), variant: "danger", divider: !m.login_active }
                          : { label: "Restore access", onClick: () => handleActivate(m.member_id), divider: !m.login_active },
                      ]}
                    />
                  </div>
                );
              })}
            </div>
          </Card>

          {coverageGaps.length > 0 && (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, padding: "14px 16px", borderRadius: 10, background: "var(--warning-bg)", border: "1px solid var(--warning-border)", marginTop: 16 }}>
              <span style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--warning-text)" }}>
                <AlertTriangle size={15}/> Assign a technician to {coverageGaps.map(c => c.name).join(", ")} before final submission.
              </span>
              {members.length > 0 && <Btn variant="secondary" size="sm" onClick={() => { setEditingMember(members[0]); setWizardOpen(true); }}>Fix assignments</Btn>}
            </div>
          )}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card>
            <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px" }}>Team readiness</p>
            {counts && (
              <>
                <div style={{ textAlign: "center", marginBottom: 14 }}>
                  <p style={{ fontSize: 34, fontWeight: 800, color: "var(--brand)", margin: 0 }}>
                    {counts.total ? Math.round((counts.ready / counts.total) * 100) : 0}%
                  </p>
                  <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>ready</p>
                </div>
                {[
                  ["Ready", counts.ready], ["Needs setup", counts.needs_setup],
                  ["Invitation pending", counts.invitation_pending], ["Disabled/offboarded", counts.disabled],
                ].map(([label, val]) => (
                  <div key={label as string} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--text-secondary)", marginBottom: 8 }}>
                    <span>{label}</span><span style={{ fontWeight: 700, color: "var(--text-primary)" }}>{val}</span>
                  </div>
                ))}
              </>
            )}
          </Card>

          <Card>
            <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>Service coverage</p>
            {coverage.length === 0 && (
              <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                No enabled services require technician coverage yet. You can continue and add your team after configuring services.
              </p>
            )}
            {coverage.map(c => (
              <div key={c.offering_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12, marginBottom: 8 }}>
                <span style={{ color: "var(--text-secondary)" }}>{c.name}</span>
                <span style={{ fontWeight: 700, color: c.ready_technician_count > 0 ? "var(--success)" : "var(--danger)" }}>
                  {c.ready_technician_count > 0
                    ? `${c.ready_technician_count} technician${c.ready_technician_count > 1 ? "s" : ""} · ${c.ready_technician_count} booking${c.ready_technician_count > 1 ? "s" : ""}/slot`
                    : "No technician"}
                </span>
              </div>
            ))}
          </Card>

          <Card>
            <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 6px" }}>Access &amp; security</p>
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0, lineHeight: 1.6 }}>
              Team members get role-based access to Fuvay. You can invite account access after setup.
            </p>
          </Card>
        </div>
      </div>

      <div style={{ position: "sticky", bottom: 0, display: "flex", justifyContent: "space-between", padding: "16px 0", marginTop: 24, background: "var(--bg-gradient)" }}>
        <Link href="/tenant/home-services/setup/coverage-availability"><Btn variant="secondary">Back</Btn></Link>
        <div style={{ display: "flex", gap: 10 }}>
          <Btn variant="secondary" onClick={load}>Save draft</Btn>
          <Btn variant="primary"
            onClick={() => router.push("/tenant/home-services/setup/finance")}>
            {coverageGaps.length > 0 ? "Continue for now" : "Save & continue"} <ChevronRight size={15}/>
          </Btn>
        </div>
      </div>

      {wizardOpen && (
        <AddTeamMemberWizard
          existing={editingMember}
          onClose={() => setWizardOpen(false)}
          onSaved={() => { setWizardOpen(false); load(); }}
        />
      )}
    </OnboardingShell>
  );
}


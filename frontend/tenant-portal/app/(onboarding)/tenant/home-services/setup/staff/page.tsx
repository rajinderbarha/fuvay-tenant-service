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
  UserPlus, Search, MoreVertical, CheckCircle2, AlertTriangle,
  ShieldOff, XCircle, ChevronRight,
} from "lucide-react";
import { OnboardingShell } from "../../../../../../components/onboarding/OnboardingShell";
import { Card, Btn, Badge, Skeleton } from "../../../../../../components/shared/ui";
import {
  providerTeamMembersApi, ServiceOSError,
  type ProviderTeamMember, type TeamReadinessSummary, type ServiceCoverageRow,
} from "../../../../../../lib/api";
import { AddTeamMemberWizard } from "../../../../../../components/onboarding/AddTeamMemberWizard";

const READINESS_META: Record<string, { label: string; variant: "default" | "success" | "warning" | "danger" | "info"; icon: React.ReactNode }> = {
  ready:                     { label: "Ready",               variant: "success", icon: <CheckCircle2 size={13}/> },
  needs_identity:            { label: "Needs identity",       variant: "warning", icon: <AlertTriangle size={13}/> },
  needs_role:                { label: "Needs role",           variant: "warning", icon: <AlertTriangle size={13}/> },
  needs_service_assignment:  { label: "Needs setup",          variant: "warning", icon: <AlertTriangle size={13}/> },
  needs_availability:        { label: "Needs setup",          variant: "warning", icon: <AlertTriangle size={13}/> },
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
  const [search, setSearch] = useState("");
  const [wizardOpen, setWizardOpen] = useState(false);
  const [editingMember, setEditingMember] = useState<ProviderTeamMember | null>(null);
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);

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

  useEffect(() => { load(); }, [load]);

  async function handleDeactivate(id: string) {
    if (!confirm("Disable access for this team member? They will no longer be able to sign in or receive new assignments.")) return;
    try { await providerTeamMembersApi.deactivate(id); load(); }
    catch (e) { setError(e instanceof ServiceOSError ? e.message : "Could not disable access."); }
    setMenuOpenId(null);
  }
  async function handleActivate(id: string) {
    try { await providerTeamMembersApi.activate(id); load(); }
    catch (e) { setError(e instanceof ServiceOSError ? e.message : "Could not restore access."); }
    setMenuOpenId(null);
  }

  const filtered = members.filter(m => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return m.full_name.toLowerCase().includes(q) || (m.email || "").toLowerCase().includes(q) || (m.phone || "").includes(q);
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

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12, marginBottom: 6 }}>
        <div>
          <p style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.06em", color: "var(--brand)", margin: "0 0 6px", textTransform: "uppercase" }}>Tenant Onboarding</p>
          <h1 style={{ fontSize: 26, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 6px" }}>Staff &amp; technicians</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>Add your team and assign the services they can perform.</p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {counts && <Badge variant={counts.total === 0 ? "info" : counts.ready === counts.total ? "success" : "warning"}>{statusLine}</Badge>}
          <Btn variant="primary" onClick={() => { setEditingMember(null); setWizardOpen(true); }}>
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

            <div style={{ border: filtered.length ? "1px solid var(--border)" : "none", borderRadius: 10, overflow: "hidden" }}>
              {filtered.map((m, i) => {
                const r = readiness?.per_member[m.member_id];
                const meta = READINESS_META[r?.status ?? "needs_identity"];
                return (
                  <div key={m.member_id} className="staff-row" style={{ borderBottom: i === filtered.length - 1 ? "none" : "1px solid var(--border)" }}>
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
                    <div style={{ position: "relative" }}>
                      <button aria-label="More actions" onClick={() => setMenuOpenId(menuOpenId === m.member_id ? null : m.member_id)} style={{
                        width: 32, height: 32, display: "flex", alignItems: "center", justifyContent: "center",
                        background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", borderRadius: 6,
                      }}><MoreVertical size={16}/></button>
                      {menuOpenId === m.member_id && (
                        <div style={{ position: "absolute", right: 0, top: 36, zIndex: 20, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, boxShadow: "var(--shadow-lg)", minWidth: 180, padding: 4 }}>
                          {m.status === "active" ? (
                            <button onClick={() => handleDeactivate(m.member_id)} style={menuItemStyle}>Disable access</button>
                          ) : (
                            <button onClick={() => handleActivate(m.member_id)} style={menuItemStyle}>Restore access</button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>

          {coverage.some(c => c.ready_technician_count === 0) && (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, padding: "14px 16px", borderRadius: 10, background: "var(--warning-bg)", border: "1px solid var(--warning-border)", marginTop: 16 }}>
              <span style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--warning-text)" }}>
                <AlertTriangle size={15}/> At least one ready technician is required for each technician-based service.
              </span>
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
                  {c.ready_technician_count > 0 ? `${c.ready_technician_count} technician${c.ready_technician_count > 1 ? "s" : ""}` : "No technician"}
                </span>
              </div>
            ))}
          </Card>

          <Card>
            <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 6px" }}>Access &amp; security</p>
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0, lineHeight: 1.6 }}>
              Team members get role-based access to the ServiceOS platform. You can invite account access after setup.
            </p>
          </Card>
        </div>
      </div>

      <div style={{ position: "sticky", bottom: 0, display: "flex", justifyContent: "space-between", padding: "16px 0", marginTop: 24, background: "var(--bg-gradient)" }}>
        <Link href="/tenant/home-services/setup/coverage-availability"><Btn variant="secondary">Back</Btn></Link>
        <div style={{ display: "flex", gap: 10 }}>
          <Btn variant="secondary" onClick={load}>Save draft</Btn>
          <Btn variant="primary"
            disabled={coverage.some(c => c.ready_technician_count === 0)}
            onClick={() => router.push("/tenant/home-services/setup/finance")}>
            Save &amp; continue <ChevronRight size={15}/>
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

const menuItemStyle: React.CSSProperties = {
  display: "block", width: "100%", textAlign: "left", padding: "8px 10px", fontSize: 13,
  color: "var(--text-primary)", background: "none", border: "none", cursor: "pointer", borderRadius: 6,
};

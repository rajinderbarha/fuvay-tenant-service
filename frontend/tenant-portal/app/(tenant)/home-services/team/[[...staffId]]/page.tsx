"use client";
import React, { Suspense, useCallback, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import {
  Users, CheckCircle2, Wrench, CircleDot, AlertTriangle, ShieldAlert,
  Search, Download, UserPlus, Phone, Mail, MapPin, Edit2,
} from "lucide-react";
import { TenantLayout } from "../../../../../components/layout/TenantLayout";
import { AddTeamMemberWizard } from "../../../../../components/onboarding/AddTeamMemberWizard";
import {
  PageShell, PageHeader, Card, StatCard, Avatar, StatusBadge, Skeleton, Alert, Button,
  Modal, Input, Select,
} from "@serviceos/design-system";
import {
  homeServicesTeamApi, providerTeamMembersApi,
  type TeamDirectoryStaffRow, type StaffOverview, type StaffCapabilities,
  type MemberType, type ProviderTeamMemberPayload,
} from "../../../../../lib/api";
import { useApi, useAction } from "../../../../../hooks/useApi";

const MEMBER_TYPE_OPTIONS: { value: MemberType; label: string }[] = [
  { value: "technician", label: "Technician" },
  { value: "staff", label: "Staff" },
  { value: "manager", label: "Manager" },
];

const DESIGNATIONS_BY_MEMBER_TYPE: Record<string, string[]> = {
  technician: [
    "Technician", "Junior Technician", "Senior Technician", "Lead Technician",
    "AC Technician", "Installation Specialist", "Maintenance Specialist", "Field Supervisor",
  ],
  staff: [
    "Operations Coordinator", "Dispatcher", "Customer Support Executive", "Back Office Executive",
  ],
  manager: [
    "Team Manager", "Operations Manager", "Service Manager", "Branch Manager",
  ],
};

const TABS = [
  { key: "overview", label: "Overview" },
  { key: "capabilities", label: "Capabilities" },
  { key: "availability", label: "Availability" },
  { key: "jobs", label: "Jobs" },
  { key: "performance", label: "Performance" },
  { key: "documents", label: "Documents" },
  { key: "activity", label: "Activity & Audit" },
] as const;
type TabKey = typeof TABS[number]["key"];

export default function TeamPage() {
  return (
    <Suspense fallback={null}>
      <TeamPageContent />
    </Suspense>
  );
}

function TeamPageContent() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();

  const staffIdParts = params.staffId as string[] | undefined;
  const selectedStaffId = staffIdParts?.[0] ?? null;
  const tab = (searchParams.get("tab") as TabKey) || "overview";

  const [search, setSearch] = useState("");
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");
  const [availability, setAvailability] = useState("");
  // Real bug fixed here: "Add team member" had no onClick at all -- it was
  // decorative. Reuses the SAME wizard the onboarding Staff & Technicians
  // step already uses (components/onboarding/AddTeamMemberWizard.tsx),
  // same fields, same providerTeamMembersApi.create() call -- not a second,
  // divergent creation form.
  const [addOpen, setAddOpen] = useState(false);

  const { data, loading, error, refetch: refetchDirectory } = useApi(
    () => homeServicesTeamApi.list({
      search: search || undefined, role: role || undefined,
      status: status || undefined, availability: availability || undefined,
    }),
    [search, role, status, availability],
  );

  const selectStaff = useCallback((staffId: string) => {
    router.push(`/home-services/team/${staffId}`);
  }, [router]);

  const setTab = useCallback((key: TabKey) => {
    if (selectedStaffId) router.replace(`/home-services/team/${selectedStaffId}?tab=${key}`);
  }, [router, selectedStaffId]);

  // Real change made here: this used to always render a split list+detail
  // panel and silently auto-selected the first team member on load (so the
  // URL never actually reflected "no one selected"). Clicking a row now
  // navigates to a genuinely dedicated full-page profile
  // (/home-services/team/{staffId}) instead of an inline split panel, and
  // the list route shows only the list -- matching the same "click a row,
  // land on a real page" pattern already used for jobs/customers elsewhere
  // in this app, and the richness of the staff member's own "My Profile"
  // page.
  if (selectedStaffId) {
    return (
      <TenantLayout activeNav="provider-staff">
        <PageShell>
          <button onClick={() => router.push("/home-services/team")}
            style={{ display: "flex", alignItems: "center", gap: 6, background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", fontSize: 13, fontFamily: "inherit", padding: 0, marginBottom: 4 }}>
            ← Back to Staff & Technicians
          </button>
          <StaffDetail staffId={selectedStaffId} tab={tab} onTabChange={setTab} onProfileUpdated={refetchDirectory} />
        </PageShell>
      </TenantLayout>
    );
  }

  return (
    <TenantLayout activeNav="provider-staff">
      <PageShell>
        <PageHeader
          title="Staff & Technicians"
          description="Manage verified team members, capabilities, availability and workload."
          actions={
            <>
              <Button variant="secondary" leftIcon={<Download size={14} />}>Export</Button>
              <Button variant="primary" leftIcon={<UserPlus size={14} />} onClick={() => setAddOpen(true)}>Add team member</Button>
            </>
          }
        />

        {error && <Alert tone="danger">{error}</Alert>}

        {loading || !data ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 16 }}>
            {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} height={90} />)}
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 16 }}>
            <StatCard icon={Users} label="Total team" value={data.summary.total_team} tone="brand" />
            <StatCard icon={CheckCircle2} label="Active" value={data.summary.active} tone="success" />
            <StatCard icon={Wrench} label="Technicians" value={data.summary.technicians} tone="info" />
            <StatCard icon={CircleDot} label="Available now" value={data.summary.available_now} tone="success" />
            <StatCard icon={AlertTriangle} label="Setup incomplete" value={data.summary.setup_incomplete} tone="warning" />
            <StatCard icon={ShieldAlert} label="Schedule conflicts" value={data.summary.schedule_conflicts} tone="danger" />
          </div>
        )}

        <Card padding="sm">
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", padding: "8px 4px 12px" }}>
            <div style={{ position: "relative", flex: "1 1 200px" }}>
              <Search size={14} style={{ position: "absolute", left: 10, top: 10, color: "var(--text-tertiary)" }} />
              <input
                value={search} onChange={e => setSearch(e.target.value)}
                placeholder="Search by name, role or capability..."
                style={{ width: "100%", padding: "8px 10px 8px 30px", borderRadius: 8, fontSize: 13,
                  border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)" }}
              />
            </div>
            <select aria-label="Staff role" value={role} onChange={e => setRole(e.target.value)}
              style={{ padding: "8px 8px", borderRadius: 8, fontSize: 12, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)" }}>
              <option value="">All roles</option>
              {(data?.available_filters.role ?? []).map(r => <option key={r} value={r}>{r}</option>)}
            </select>
            <select aria-label="Staff status" value={status} onChange={e => setStatus(e.target.value)}
              style={{ padding: "8px 8px", borderRadius: 8, fontSize: 12, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)" }}>
              <option value="">All statuses</option>
              {(data?.available_filters.status ?? []).map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <select aria-label="Staff availability" value={availability} onChange={e => setAvailability(e.target.value)}
              style={{ padding: "8px 8px", borderRadius: 8, fontSize: 12, border: "1px solid var(--border)", background: "var(--surface-sunken)", color: "var(--text-primary)" }}>
              <option value="">All availability</option>
              {(data?.available_filters.availability ?? []).map(a => <option key={a} value={a}>{a}</option>)}
            </select>
          </div>

          {!loading && data && data.staff.length === 0 ? (
            <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-tertiary)", fontSize: 13 }}>
              {search || role || status || availability ? "No team members match these filters." : "No team members yet."}
            </div>
          ) : (
            <div>
              {(data?.staff ?? []).map(s => (
                <StaffRow key={s.staff_id} staff={s} selected={false}
                  onClick={() => selectStaff(s.staff_id)} />
              ))}
            </div>
          )}
        </Card>
      </PageShell>

      {addOpen && (
        <AddTeamMemberWizard
          existing={null}
          onClose={() => setAddOpen(false)}
          onSaved={() => { setAddOpen(false); refetchDirectory(); }}
        />
      )}
    </TenantLayout>
  );
}

function StaffRow({ staff, selected, onClick }: { staff: TeamDirectoryStaffRow; selected: boolean; onClick: () => void }) {
  const readyTone = staff.capacity_state === "ready" ? "var(--success)" : staff.capacity_state === "at_risk" ? "var(--danger)" : "var(--warning)";
  const readyLabel = staff.capacity_state === "ready" ? "Ready" : staff.capacity_state === "at_risk" ? "At risk" : "Incomplete";
  return (
    <div onClick={onClick} role="button" tabIndex={0}
      onKeyDown={e => { if (e.key === "Enter" || e.key === " ") onClick(); }}
      style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 8px", borderRadius: 8,
        cursor: "pointer", background: selected ? "var(--accent-muted)" : "transparent",
        border: selected ? "1px solid var(--brand)" : "1px solid transparent", marginBottom: 2 }}>
      <Avatar src={staff.photo} name={staff.name} size={36} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600, fontSize: 13.5, color: "var(--text-primary)" }}>{staff.name}</div>
        <div style={{ fontSize: 11.5, color: "var(--text-tertiary)", textTransform: "capitalize" }}>{staff.role}</div>
      </div>
      <div style={{ textAlign: "right", minWidth: 42 }}>
        <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{staff.capacity_used} / {staff.capacity_limit}</div>
      </div>
      <div style={{ width: 40, height: 40, borderRadius: "50%", flexShrink: 0,
        background: `conic-gradient(${readyTone} ${staff.capacity_percentage * 3.6}deg, var(--surface-sunken) 0deg)`,
        display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ width: 32, height: 32, borderRadius: "50%", background: "var(--surface)",
          display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 700, color: readyTone }}>
          {staff.capacity_percentage}%
        </div>
      </div>
      <div style={{ minWidth: 62, textAlign: "right" }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: readyTone }}>{readyLabel}</div>
        <div style={{ fontSize: 10, color: "var(--text-tertiary)" }}>
          {staff.conflict_count > 0 ? "Busy (Conflict)" : staff.availability_status === "available" ? "Available" : "Not available"}
        </div>
      </div>
    </div>
  );
}

function StaffDetail({ staffId, tab, onTabChange, onProfileUpdated }: {
  staffId: string; tab: TabKey; onTabChange: (t: TabKey) => void; onProfileUpdated: () => void;
}) {
  const { data: overview, loading, error, refetch: refetchOverview } = useApi(() => homeServicesTeamApi.overview(staffId), [staffId]);
  const [editOpen, setEditOpen] = useState(false);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card>
        {loading || !overview ? <Skeleton height={70} /> : error ? <Alert tone="danger">{error}</Alert> : (
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <Avatar src={overview.identity.photo} name={overview.identity.name} size={56} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>{overview.identity.name}</div>
              <div style={{ fontSize: 13, color: "var(--text-tertiary)", textTransform: "capitalize" }}>
                {overview.identity.designation || overview.identity.role}
              </div>
              <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
                <StatusBadge status={overview.employment_status} size="sm" />
                <StatusBadge status={overview.verification_status} size="sm" />
                <StatusBadge status={overview.availability_status} size="sm" />
              </div>
            </div>
            <Button variant="secondary" size="sm" leftIcon={<Edit2 size={13} />} onClick={() => setEditOpen(true)}>
              Edit profile
            </Button>
          </div>
        )}
      </Card>

      {editOpen && (
        <EditProfileModal
          staffId={staffId}
          onClose={() => setEditOpen(false)}
          onSaved={() => { setEditOpen(false); refetchOverview(); onProfileUpdated(); }}
        />
      )}

      <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", overflowX: "auto" }}>
        {TABS.map(t => (
          <button key={t.key} onClick={() => onTabChange(t.key)}
            style={{
              padding: "9px 12px", background: "none", border: "none", cursor: "pointer",
              fontSize: 12.5, fontWeight: 600, whiteSpace: "nowrap",
              color: tab === t.key ? "var(--brand)" : "var(--text-tertiary)",
              borderBottom: tab === t.key ? "2px solid var(--brand)" : "2px solid transparent",
            }}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" && <OverviewTab overview={overview} loading={loading} error={error} />}
      {tab === "capabilities" && <CapabilitiesTab staffId={staffId} />}
      {tab !== "overview" && tab !== "capabilities" && (
        <Card>
          <div style={{ textAlign: "center", padding: "28px 0", color: "var(--text-tertiary)", fontSize: 13 }}>
            This tab isn&apos;t built yet — coming in a follow-up pass.
          </div>
        </Card>
      )}
    </div>
  );
}

function EditProfileModal({ staffId, onClose, onSaved }: { staffId: string; onClose: () => void; onSaved: () => void }) {
  const { data: member, loading: memberLoading, error: memberError } = useApi(
    () => providerTeamMembersApi.get(staffId), [staffId],
  );

  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [designation, setDesignation] = useState("");
  const [memberType, setMemberType] = useState<MemberType>("technician");
  const [canReceiveAssignment, setCanReceiveAssignment] = useState(true);
  const [initialized, setInitialized] = useState(false);
  const designationOptions = [
    ...(designation && !(DESIGNATIONS_BY_MEMBER_TYPE[memberType] ?? []).includes(designation) ? [designation] : []),
    ...(DESIGNATIONS_BY_MEMBER_TYPE[memberType] ?? []),
  ].map(value => ({ value, label: value }));

  if (member && !initialized) {
    setFullName(member.full_name ?? "");
    setPhone(member.phone ?? "");
    setEmail(member.email ?? "");
    setDesignation(member.designation ?? "");
    setMemberType((member.member_type as MemberType) ?? "technician");
    setCanReceiveAssignment(member.can_receive_assignment ?? true);
    setInitialized(true);
  }

  const { execute: save, loading: saving, error: saveError } = useAction(
    (payload: Partial<ProviderTeamMemberPayload>) => providerTeamMembersApi.update(staffId, payload),
    { onSuccess: onSaved },
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!fullName.trim() || !designation.trim()) return;
    await save({
      full_name: fullName.trim(),
      phone: phone.trim() || null,
      email: email.trim() || null,
      designation: designation.trim() || null,
      member_type: memberType,
      can_receive_assignment: canReceiveAssignment,
    });
  }

  return (
    <Modal open onClose={onClose} title="Edit profile">
      {memberLoading || !member ? (
        memberError ? <Alert tone="danger">{memberError}</Alert> : <Skeleton height={220} />
      ) : (
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {saveError && <Alert tone="danger">{saveError}</Alert>}
          <Input label="Full name" required value={fullName} onChange={e => setFullName(e.target.value)} />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Input label="Phone" value={phone} onChange={e => setPhone(e.target.value)} />
            <Input label="Email" type="email" value={email} onChange={e => setEmail(e.target.value)} />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Select label="Role" options={MEMBER_TYPE_OPTIONS} value={memberType}
              onChange={e => {
                const nextType = e.target.value as MemberType;
                setMemberType(nextType);
                if (!(DESIGNATIONS_BY_MEMBER_TYPE[nextType] ?? []).includes(designation)) setDesignation("");
              }} />
            <Select label="Designation" required options={designationOptions} value={designation}
              placeholder="Select designation" onChange={e => setDesignation(e.target.value)} />
          </div>
          <div style={{ padding: "10px 12px", borderRadius: 8, background: "var(--surface-sunken)", border: "1px solid var(--border)" }}>
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-secondary)", paddingBottom: 8 }}>
              <input type="checkbox" checked={canReceiveAssignment}
                onChange={e => setCanReceiveAssignment(e.target.checked)} />
              Can receive new job assignments
            </label>
            <p style={{ margin: 0, fontSize: 11, color: "var(--text-tertiary)" }}>
              Slot capacity is calculated automatically from ready technicians assigned to the service.
            </p>
          </div>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 4 }}>
            <Button type="button" variant="secondary" onClick={onClose} disabled={saving}>Cancel</Button>
            <Button type="submit" variant="primary" loading={saving}>Save changes</Button>
          </div>
        </form>
      )}
    </Modal>
  );
}

function OverviewTab({ overview, loading, error }: { overview: StaffOverview | null; loading: boolean; error: string | null }) {
  if (loading || !overview) return <Skeleton height={280} />;
  if (error) return <Alert tone="danger">{error}</Alert>;

  const checklistLabels: Record<string, string> = {
    identity_verified: "Identity verified",
    employment_active: "Employment active",
    capabilities_configured: "Capabilities configured",
    availability_configured: "Availability configured",
  };
  const ringTone = overview.today.capacity_percentage >= 100 ? "var(--danger)"
    : overview.today.capacity_percentage >= 75 ? "var(--warning)" : "var(--success)";

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 14 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
        <Card title="Profile & contact">
          <Row icon={<Phone size={13} />} value={overview.identity.phone ?? "—"} />
          <Row icon={<Mail size={13} />} value={overview.identity.email ?? "—"} />
          <Row icon={<MapPin size={13} />} value={overview.joined_at ? `Joined ${new Date(overview.joined_at).toLocaleDateString()}` : "—"} />
        </Card>

        <Card title="Today's schedule">
          {overview.today.schedule.length === 0 ? (
            <div style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No jobs scheduled today.</div>
          ) : (
            overview.today.schedule.map(j => (
              <div key={j.job_id} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0",
                borderBottom: "1px solid var(--border)", fontSize: 13 }}>
                <span>{j.job_number}{j.time_window ? ` · ${j.time_window}` : ""}</span>
                <StatusBadge status={j.status} size="sm" />
              </div>
            ))
          )}
        </Card>

        <Card title="Service capabilities">
          {overview.supported_services.length === 0 ? (
            <div style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No service capability configured yet.</div>
          ) : (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {overview.supported_services.map(s => (
                <span key={s.id} style={{ fontSize: 12, padding: "4px 10px", borderRadius: 999,
                  background: "var(--surface-sunken)", border: "1px solid var(--border)" }}>{s.name}</span>
              ))}
            </div>
          )}
        </Card>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <Card title="Capacity today">
          <div style={{ display: "flex", justifyContent: "center", padding: "10px 0" }}>
            <div style={{ width: 110, height: 110, borderRadius: "50%",
              background: `conic-gradient(${ringTone} ${overview.today.capacity_percentage * 3.6}deg, var(--surface-sunken) 0deg)`,
              display: "flex", alignItems: "center", justifyContent: "center" }}>
              <div style={{ width: 88, height: 88, borderRadius: "50%", background: "var(--surface)",
                display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
                <div style={{ fontSize: 20, fontWeight: 800, color: "var(--text-primary)" }}>
                  {overview.today.capacity_used}/{overview.today.capacity_limit}
                </div>
                <div style={{ fontSize: 10.5, color: "var(--text-tertiary)" }}>jobs</div>
              </div>
            </div>
          </div>
        </Card>

        <Card title="Readiness checklist">
          {Object.entries(overview.readiness.checklist).map(([key, val]) => (
            <div key={key} style={{ display: "flex", alignItems: "center", gap: 8, padding: "5px 0", fontSize: 13 }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%",
                background: val ? "var(--success)" : "var(--warning)" }} />
              {checklistLabels[key] ?? key}
            </div>
          ))}
        </Card>

        {overview.next_assignment && (
          <Card title="Next assignment">
            <div style={{ fontSize: 13 }}>{overview.next_assignment.job_number}</div>
            <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
              {overview.next_assignment.scheduled_date} {overview.next_assignment.time_window}
            </div>
          </Card>
        )}

        {overview.schedule_conflicts > 0 && (
          <Alert tone="danger">{overview.schedule_conflicts} schedule conflict(s) require review.</Alert>
        )}
      </div>
    </div>
  );
}

function CapabilitiesTab({ staffId }: { staffId: string }) {
  const { data, loading, error } = useApi(() => homeServicesTeamApi.capabilities(staffId), [staffId]);
  if (loading || !data) return <Skeleton height={280} />;
  if (error) return <Alert tone="danger">{error}</Alert>;

  if (data.services.length === 0) {
    return (
      <Card>
        <div style={{ textAlign: "center", padding: "28px 0", color: "var(--text-tertiary)", fontSize: 13 }}>
          No capability configured yet for this team member.
        </div>
      </Card>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {data.services.map(svc => (
        <Card key={svc.offering_id} title={svc.master_service}>
          <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginBottom: 10 }}>
            {[svc.category, svc.service_group].filter(Boolean).join(" · ") || "Home Services"}
          </div>
          {svc.requires_type && <CapabilityGroup label="Type" items={svc.types} />}
          {svc.requires_brand && <CapabilityGroup label="Brand" items={svc.brands} />}
          {!svc.requires_type && !svc.requires_brand && (
            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>No type/brand dimension for this service.</div>
          )}
        </Card>
      ))}
    </div>
  );
}

function CapabilityGroup({ label, items }: { label: string; items: { id: string; name: string; supported: boolean }[] }) {
  if (items.length === 0) return null;
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-tertiary)", marginBottom: 6 }}>{label}</div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {items.map(i => (
          <span key={i.id} style={{
            fontSize: 12, padding: "4px 10px", borderRadius: 999,
            background: i.supported ? "var(--success-bg)" : "var(--surface-sunken)",
            border: `1px solid ${i.supported ? "var(--success-border)" : "var(--border)"}`,
            color: i.supported ? "var(--success-text)" : "var(--text-tertiary)",
          }}>
            {i.name}
          </span>
        ))}
      </div>
    </div>
  );
}

function Row({ icon, value }: { icon: React.ReactNode; value: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0", fontSize: 13, color: "var(--text-secondary)" }}>
      <span style={{ color: "var(--text-tertiary)" }}>{icon}</span>
      {value}
    </div>
  );
}

"use client";
/**
 * Provider 360° detail workspace — the SAME component is mounted at both
 * the dedicated Home Services route (/admin/home-services/providers/{id})
 * and the generic per-vertical route (/admin/{vertical}/providers/{id}),
 * so the URL shape and design are identical no matter which vertical the
 * provider belongs to. Only Home Services has a real backend directory
 * service today (HomeServicesProviderDirectoryService); other verticals'
 * pages route here too but the caller (app/admin/[vertical]/providers/[id]
 * /page.tsx) shows an honest "not available yet" state instead of mounting
 * this component when the vertical isn't Home Services -- nothing here is
 * vertical-agnostic by pretending to be, it's vertical-agnostic by URL/
 * design only.
 */
import { useCallback, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ShieldCheck, ArrowLeft, FileText, Wrench, Users, Briefcase, Star,
  Wallet, ShieldCheck as DepositIcon, AlertTriangle, ChevronRight, MoreHorizontal,
  PauseCircle, RotateCcw, Send,
} from "lucide-react";
import { AdminLayout } from "../layout/AdminLayout";
import { Card, Badge, Btn, Skeleton, Modal, DataTable } from "../shared/ui";
import { hsProviderDirectoryApi, hsReviewApi, verticalCatalogApi } from "../../lib/api";
import { useApi, useAction } from "../../hooks/useApi";

function dt(v?: string | null) {
  return v ? new Date(v).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—";
}
function money(v?: string | number | null) {
  return `₹${Number(v ?? 0).toLocaleString("en-IN")}`;
}

const TABS = [
  { key: "overview", label: "Overview" },
  { key: "verification", label: "Business & Verification" },
  { key: "services", label: "Services & Coverage" },
  { key: "team", label: "Team & Capacity" },
  { key: "operations", label: "Operations" },
  { key: "finance", label: "Finance" },
  { key: "quality", label: "Quality & Complaints" },
  { key: "documents", label: "Documents & Activity" },
] as const;
type TabKey = typeof TABS[number]["key"];

export function ProviderDetailWorkspace({ providerId, basePath, breadcrumbVertical }: {
  providerId: string;
  /** URL prefix this instance is mounted under, e.g. "/admin/home-services/providers". */
  basePath: string;
  breadcrumbVertical?: string;
}) {
  const router = useRouter();
  const search = useSearchParams();
  const tab = (search.get("tab") as TabKey) || "overview";
  const [auditOpen, setAuditOpen] = useState(false);
  const [action, setAction] = useState<"changes_requested" | "suspended" | "approved_pending_activation" | null>(null);
  const [reason, setReason] = useState("");
  const [notice, setNotice] = useState<string | null>(null);

  const detail = useApi(useCallback(() => hsProviderDirectoryApi.getDetail(providerId), [providerId]));
  const enrollment = useApi(useCallback(
    () => verticalCatalogApi.listEnrollments("home_services", { tenant_id: providerId }),
    [providerId],
  ));
  const transition = useAction(useCallback(
    (enrollmentId: string, status: string, note: string) =>
      verticalCatalogApi.transitionEnrollment(enrollmentId, status, note),
    [],
  ));

  function setTab(t: TabKey) {
    router.replace(`${basePath}/${providerId}?tab=${t}`);
  }
  function backToProviders() {
    router.back();
  }

  async function submitLifecycleAction() {
    const row = enrollment.data?.items?.[0];
    if (!row || !action || !reason.trim()) return;
    const result = await transition.execute(row.id, action, reason.trim());
    if (result) {
      setNotice(
        action === "changes_requested" ? "Change request sent to the provider." :
        action === "suspended" ? "Home Services enrollment suspended." :
        "Home Services enrollment returned to activation review.",
      );
      setAction(null); setReason("");
      enrollment.refetch(); detail.refetch();
    }
  }

  if (detail.loading) return <AdminLayout activeNav="home_services-providers"><Skeleton height={400} /></AdminLayout>;
  if (detail.error) {
    return (
      <AdminLayout activeNav="home_services-providers">
        <Card padding={24}>
          <p style={{ color: "var(--danger-text)" }}>
            {detail.error.includes("404") || detail.error.toLowerCase().includes("not found")
              ? "This provider was not found, or does not have a Home Services assignment."
              : `Failed to load provider: ${detail.error}`}
          </p>
          <Btn variant="ghost" icon={<ArrowLeft size={14} />} onClick={backToProviders}>Back to Providers</Btn>
        </Card>
      </AdminLayout>
    );
  }
  const d = detail.data as Record<string, unknown> | undefined;
  if (!d) return null;

  const addr = d.address as Record<string, unknown> | undefined;
  const isActive = d.registration_status === "active";
  const isVerified = d.verification_status === "approved";
  const isBookable = Boolean(d.is_discoverable);
  const enrollmentRow = enrollment.data?.items?.[0];
  const enrollmentStatus = enrollmentRow?.status;

  return (
    <AdminLayout activeNav="home_services-providers">
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4, fontSize: 12, color: "var(--text-tertiary)" }}>
        <span>Operations</span><ChevronRight size={12} /><span>{breadcrumbVertical ?? "Home Services"}</span><ChevronRight size={12} />
        <span>Providers</span><ChevronRight size={12} />
        <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{String(d.business_name ?? "Provider")}</span>
      </div>
      <button onClick={backToProviders}
        style={{ display: "flex", alignItems: "center", gap: 6, background: "none", border: "none", color: "var(--text-tertiary)", fontSize: 12, cursor: "pointer", padding: 0, marginBottom: 12 }}>
        <ArrowLeft size={13} /> Back to Providers
      </button>

      {/* ── Identity header ─────────────────────────────────────────────── */}
      <Card padding={20} style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
        <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
          <div style={{ width: 56, height: 56, borderRadius: 12, background: "var(--brand)", display: "flex",
            alignItems: "center", justifyContent: "center", overflow: "hidden", flexShrink: 0 }}>
            {d.logo_url
              ? <img src={String(d.logo_url)} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              : <span style={{ fontWeight: 800, fontSize: 20, color: "white" }}>{String(d.business_name ?? "?").charAt(0)}</span>}
          </div>
          <div>
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>{String(d.business_name ?? "—")}</h1>
              <Badge variant="info">{breadcrumbVertical ?? "Home Services"}</Badge>
              <Badge variant={isActive ? "success" : d.registration_status === "suspended" ? "danger" : "default"}>
                {isActive ? "Active" : String(d.registration_status)}
              </Badge>
              <Badge variant={isVerified ? "success" : "default"}>{isVerified ? "Verified" : String(d.verification_status)}</Badge>
              <Badge variant={isBookable ? "info" : "muted"}>{isBookable ? "Bookable" : "Not Bookable"}</Badge>
              {enrollmentStatus && <Badge variant={enrollmentStatus === "active" ? "success" : enrollmentStatus === "suspended" ? "danger" : "warning"}>
                Home Services: {enrollmentStatus.replace(/_/g, " ")}
              </Badge>}
            </div>
            <div style={{ display: "flex", gap: 16, marginTop: 6, fontSize: 12, color: "var(--text-tertiary)", flexWrap: "wrap" }}>
              <span>Provider ID: {String(d.tenant_code ?? providerId.slice(0, 8))}</span>
              <span>Owner: {String(d.owner_name ?? "—")}</span>
              <span>{String(addr?.city ?? "—")}, {String(addr?.state ?? "—")}</span>
              <span>Member since {dt(d.created_at as string)}</span>
            </div>
            {(d.additional_vertical_assignments as number) > 0 && (
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 6 }}>
                This business has {String(d.additional_vertical_assignments)} additional vertical assignment(s).
              </p>
            )}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <Btn variant="ghost" icon={<FileText size={14} />} onClick={() => setAuditOpen(true)}>Lifecycle Record</Btn>
          <Btn variant="ghost" icon={<Send size={14}/>} disabled={!enrollmentRow}
            onClick={() => { setAction("changes_requested"); setReason(""); }}>
            Request Changes
          </Btn>
          {enrollmentStatus === "suspended" ? (
            <Btn variant="success" icon={<RotateCcw size={14}/>} disabled={!enrollmentRow}
              onClick={() => { setAction("approved_pending_activation"); setReason(""); }}>
              Resume Home Services
            </Btn>
          ) : (
            <Btn variant="danger" icon={<PauseCircle size={14}/>} disabled={!enrollmentRow}
              onClick={() => { setAction("suspended"); setReason(""); }}>
              Suspend Home Services
            </Btn>
          )}
          <button style={{ background: "none", border: "1px solid var(--border)", borderRadius: 8, width: 32, height: 32,
            display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", color: "var(--text-tertiary)" }}>
            <MoreHorizontal size={16} />
          </button>
        </div>
      </Card>

      {notice && (
        <div role="status" style={{ marginTop: 12, padding: "10px 14px", borderRadius: 10,
          background: "var(--success-bg)", border: "1px solid var(--success-border)", color: "var(--success-text)", fontSize: 13 }}>
          {notice}
        </div>
      )}

      <Card padding={12} style={{ marginTop: 12, background: "var(--surface-sunken)", display: "flex", gap: 8, alignItems: "flex-start" }}>
        <AlertTriangle size={14} style={{ color: "var(--text-tertiary)", flexShrink: 0, marginTop: 1 }} />
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
          Actions on this page affect only the Home Services assignment. Other verticals are unaffected.
        </p>
      </Card>

      <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", margin: "16px 0", overflowX: "auto" }}>
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            style={{ padding: "10px 14px", fontSize: 13, fontWeight: 600, background: "none", border: "none",
              borderBottom: tab === t.key ? "2px solid var(--brand)" : "2px solid transparent",
              color: tab === t.key ? "var(--text-primary)" : "var(--text-tertiary)", cursor: "pointer", whiteSpace: "nowrap" }}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" && <OverviewTab d={d} providerId={providerId} />}
      {tab === "verification" && <VerificationTab d={d} />}
      {tab === "finance" && <FinanceTab providerId={providerId} />}
      {tab === "quality" && <QualityTab providerId={providerId} />}
      {tab === "team" && <TeamTab providerId={providerId} />}
      {tab === "operations" && <OperationsTab providerId={providerId} />}
      {tab === "documents" && <ActivityTab providerId={providerId} />}
      {tab === "services" && <ServicesTab providerId={providerId} />}

      <Modal open={auditOpen} onClose={() => setAuditOpen(false)} title="Home Services lifecycle" size="lg">
        <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 14 }}>
          Enrollment decisions are audited independently from the provider&apos;s other business operations.
        </p>
        <DataTable rows={enrollment.data?.items ?? []} emptyText="No Home Services enrollment found."
          columns={[
            { key: "status", label: "Status", render: v => <Badge variant={v === "active" ? "success" : v === "suspended" ? "danger" : "info"}>{String(v).replace(/_/g, " ")}</Badge> },
            { key: "requested_at", label: "Requested", render: v => dt(v as string) },
            { key: "reviewed_at", label: "Last reviewed", render: v => dt(v as string) },
            { key: "suspend_reason", label: "Latest reason", render: (v, row) => String(v || row.changes_requested_note || row.rejection_reason || "—") },
          ]}
        />
      </Modal>

      <Modal open={action !== null} onClose={() => { setAction(null); setReason(""); }}
        title={action === "changes_requested" ? "Request provider changes" : action === "suspended" ? "Suspend Home Services" : "Resume Home Services"}>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
            This affects only the provider&apos;s Home Services enrollment. Enter a clear reason for the audit trail and provider communication.
          </p>
          <textarea value={reason} onChange={e => setReason(e.target.value)} rows={4}
            aria-label="Action reason" placeholder="Reason is required"
            style={{ width: "100%", resize: "vertical", padding: 12, borderRadius: 10,
              border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", fontFamily: "inherit" }} />
          {transition.error && <p role="alert" style={{ color: "var(--danger-text)", fontSize: 12, margin: 0 }}>{transition.error}</p>}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <Btn variant="secondary" onClick={() => { setAction(null); setReason(""); }}>Cancel</Btn>
            <Btn variant={action === "suspended" ? "danger" : "primary"} loading={transition.loading}
              disabled={!reason.trim()} onClick={submitLifecycleAction}>Confirm action</Btn>
          </div>
        </div>
      </Modal>
    </AdminLayout>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ fontSize: 10, textTransform: "uppercase", color: "var(--text-tertiary)", marginBottom: 2 }}>{label}</div>
      <div style={{ fontWeight: 600 }}>{value}</div>
    </div>
  );
}
function ReadinessRow({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <ShieldCheck size={14} color={ok ? "var(--success-text, #0a7c3f)" : "var(--text-tertiary)"} />
      <span style={{ color: ok ? "var(--text-primary)" : "var(--text-tertiary)" }}>{label}</span>
    </div>
  );
}
function StatCard({ label, value, sub, icon, alert }: { label: string; value: string; sub?: string; icon?: React.ReactNode; alert?: boolean }) {
  return (
    <Card padding={14} style={alert ? { borderColor: "var(--warning-border, var(--warning))" } : undefined}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {icon && <span style={{ color: alert ? "var(--warning-text)" : "var(--text-tertiary)" }}>{icon}</span>}
        <div style={{ fontSize: 20, fontWeight: 800 }}>{value}</div>
      </div>
      <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>{label}{sub ? ` · ${sub}` : ""}</div>
    </Card>
  );
}

// ── Overview: consolidated dashboard, composed from the same real
// per-tab endpoints used elsewhere on this page. ──────────────────────────
function OverviewTab({ d, providerId }: { d: Record<string, unknown>; providerId: string }) {
  const readiness = d.readiness as Record<string, boolean> | undefined;
  const finance = useApi(useCallback(() => hsProviderDirectoryApi.getFinance(providerId), [providerId]));
  const quality = useApi(useCallback(() => hsProviderDirectoryApi.getQuality(providerId), [providerId]));
  const team = useApi(useCallback(() => hsProviderDirectoryApi.getTeam(providerId), [providerId]));
  const ops = useApi(useCallback(() => hsProviderDirectoryApi.getOperations(providerId), [providerId]));
  const services = useApi(useCallback(() => hsProviderDirectoryApi.getServices(providerId), [providerId]));
  const reviews = useApi(useCallback(() => hsReviewApi.getProviderReviewSummary("home-services", providerId), [providerId]));

  const f = finance.data as Record<string, unknown> | undefined;
  const q = quality.data as Record<string, unknown> | undefined;
  const t = team.data as Record<string, unknown> | undefined;
  const o = ops.data as Record<string, unknown> | undefined;
  const s = services.data as Record<string, unknown> | undefined;
  const rs = reviews.data?.summary as Record<string, unknown> | null | undefined;

  const credits = f?.usage_credits as Record<string, unknown> | undefined;
  const deposit = f?.security_deposit as Record<string, unknown> | undefined;
  const byStatus = (o?.by_status ?? {}) as Record<string, number>;
  const jobs = ((o?.jobs ?? []) as Record<string, unknown>[]).slice(0, 6);
  const complaints = (q?.complaints ?? []) as Record<string, unknown>[];

  // Attention list: only real, currently-true signals — nothing invented.
  const attention: { label: string; severity: "high" | "medium" }[] = [];
  if (readiness?.admin_hold_active) attention.push({ label: "Admin hold is currently active on this tenant", severity: "high" });
  if (t && Number(t.total_staff ?? 0) > 0 && Number(t.verified_staff ?? 0) < Number(t.total_staff ?? 0)) {
    attention.push({ label: `${Number(t.total_staff) - Number(t.verified_staff)} staff verification(s) pending`, severity: "medium" });
  }
  if (t && Number(t.capability_incomplete_staff ?? 0) > 0) {
    attention.push({ label: `${t.capability_incomplete_staff} staff member(s) with incomplete job-type capabilities`, severity: "medium" });
  }
  if (s && Number(s.missing_price_config_count ?? 0) > 0) {
    attention.push({ label: `${s.missing_price_config_count} service(s) missing price configuration`, severity: "medium" });
  }
  if (q && Number(q.open_complaints_count ?? 0) > 0) {
    attention.push({ label: `${q.open_complaints_count} complaint(s) awaiting resolution`, severity: "high" });
  }
  if (credits?.low_balance) attention.push({ label: "Usage credit balance is low", severity: "medium" });

  return (
    <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 16, gridColumn: "1 / -1" }}>
        {/* Top stat strip */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12 }}>
          <StatCard label="Health" value={`${Number(d.health_score ?? 0)}%`} sub={String(d.health_band ?? "")} />
          <StatCard label="Active Services" value={services.loading ? "…" : String(s?.active_services ?? 0)} icon={<Wrench size={15} />} />
          <StatCard label="Staff / Available" value={team.loading ? "…" : `${t?.total_staff ?? 0} / ${t?.available_staff ?? 0}`} icon={<Users size={15} />} />
          <StatCard label="Active Jobs" value={ops.loading ? "…" : String(o?.active_jobs ?? 0)} icon={<Briefcase size={15} />} />
          <StatCard label="Rating" value={rs ? Number(rs.average_rating).toFixed(1) : Number(d.rating_average ?? 0).toFixed(1)}
            sub={rs ? `${rs.total_reviews} reviews` : undefined} icon={<Star size={15} />} />
          <StatCard label="Usage Credits" value={finance.loading ? "…" : money(credits?.balance as string)} icon={<Wallet size={15} />} alert={Boolean(credits?.low_balance)} />
          <StatCard label="Security Deposit" value={finance.loading ? "…" : money(deposit?.current_balance as string)} icon={<DepositIcon size={15} />} />
          {attention.length > 0 && (
            <StatCard label="Items need attention" value={String(attention.length)} icon={<AlertTriangle size={15} />} alert />
          )}
        </div>
      </div>

      {/* Left column */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <Card padding={16}>
          <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>Business & activation readiness</h3>
          {readiness ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13 }}>
              <ReadinessRow ok={readiness.business_verification_complete} label="Business verification complete" />
              <ReadinessRow ok={readiness.security_deposit_active} label="Security deposit active" />
              <ReadinessRow ok={readiness.credit_account_healthy} label="Credit account healthy" />
              <ReadinessRow ok={!readiness.admin_hold_active} label="No blocking admin hold" />
            </div>
          ) : <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Not available.</p>}
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 10 }}>
            Service readiness, staff readiness and bookability aren&apos;t wired into this checklist yet —
            they need canonical read services this page doesn&apos;t reach into. Shown only when backed by a
            real check, never guessed.
          </p>
        </Card>

        <Card padding={16}>
          <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>Current operations</h3>
          {ops.loading ? <Skeleton height={80} /> : Object.keys(byStatus).length === 0 ? (
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>No Home Services jobs recorded for this provider yet.</p>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(100px, 1fr))", gap: 10 }}>
              {Object.entries(byStatus).map(([status, count]) => (
                <div key={status} style={{ textAlign: "center", padding: "8px 4px", background: "var(--surface-sunken)", borderRadius: 8 }}>
                  <div style={{ fontSize: 16, fontWeight: 800 }}>{count}</div>
                  <div style={{ fontSize: 10, color: "var(--text-tertiary)", textTransform: "capitalize" }}>{status.replace(/_/g, " ")}</div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card padding={16}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
            <h3 style={{ fontSize: 13, fontWeight: 700, margin: 0 }}>Recent jobs</h3>
          </div>
          <DataTable
            rows={jobs}
            emptyText="No Home Services jobs recorded for this provider yet."
            columns={[
              { key: "job_number", label: "Job #" },
              { key: "status", label: "Status", render: v => <Badge variant={v === "completed" ? "success" : v === "cancelled" ? "danger" : "default"}>{String(v)}</Badge> },
              { key: "assignment_status", label: "Assignment", render: v => v ? String(v) : "—" },
              { key: "updated_at", label: "Last Update", render: v => dt(v as string) },
            ]}
          />
        </Card>
      </div>

      {/* Right column */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <Card padding={16}>
          <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>Attention required</h3>
          {attention.length === 0 ? (
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>Nothing needs attention right now.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {attention.map((a, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                  <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{a.label}</span>
                  <Badge variant={a.severity === "high" ? "danger" : "warning"} size="sm">{a.severity}</Badge>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card padding={16}>
          <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>Team & capacity</h3>
          {team.loading ? <Skeleton height={70} /> : (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: 12 }}>
              <div><span style={{ color: "var(--text-tertiary)" }}>Total staff </span><strong>{String(t?.total_staff ?? 0)}</strong></div>
              <div><span style={{ color: "var(--text-tertiary)" }}>Available </span><strong>{String(t?.available_staff ?? 0)}</strong></div>
              <div><span style={{ color: "var(--text-tertiary)" }}>Verified </span><strong>{String(t?.verified_staff ?? 0)}</strong></div>
              <div><span style={{ color: "var(--text-tertiary)" }}>Suspended </span><strong>{String(t?.suspended_staff ?? 0)}</strong></div>
            </div>
          )}
        </Card>

        <Card padding={16}>
          <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>Quality & customer experience</h3>
          {quality.loading ? <Skeleton height={80} /> : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-tertiary)" }}>Average rating</span>
                <strong>{rs ? `${Number(rs.average_rating).toFixed(1)} ★ (${rs.total_reviews} reviews)` : "—"}</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-tertiary)" }}>Open complaints</span>
                <strong>{String(q?.open_complaints_count ?? 0)}</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-tertiary)" }}>Total complaints</span>
                <strong>{String(q?.total_complaints ?? 0)}</strong>
              </div>
            </div>
          )}
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 10 }}>
            Completion rate, cancellation rate and repeat-customer rate aren&apos;t wired into this tab yet.
          </p>
        </Card>

        <Card padding={16}>
          <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>Finance snapshot</h3>
          {finance.loading ? <Skeleton height={90} /> : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-tertiary)" }}>Usage credits</span><strong>{money(credits?.balance as string)}</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-tertiary)" }}>Security deposit</span><strong>{String(deposit?.status ?? "not_required")}</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-tertiary)" }}>Deposit held</span><strong>{money(deposit?.current_balance as string)}</strong>
              </div>
              <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "4px 0 0" }}>{String(f?.customer_payment_note ?? "")}</p>
            </div>
          )}
        </Card>

        <Card padding={16}>
          <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 6px" }}>Services & coverage</h3>
          {services.loading ? <Skeleton height={60} /> : (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: 12 }}>
              <div><span style={{ color: "var(--text-tertiary)" }}>Total </span><strong>{String(s?.total_services ?? 0)}</strong></div>
              <div><span style={{ color: "var(--text-tertiary)" }}>Published </span><strong>{String(s?.published_services ?? 0)}</strong></div>
              <div><span style={{ color: "var(--text-tertiary)" }}>Priced </span><strong>{String(s?.price_configured_count ?? 0)}</strong></div>
              <div><span style={{ color: "var(--text-tertiary)" }}>Missing price </span><strong>{String(s?.missing_price_config_count ?? 0)}</strong></div>
            </div>
          )}
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 8 }}>
            Pricing ownership: Tenant-owned. Serviceable-area coverage isn&apos;t wired into this tab yet.
          </p>
        </Card>
      </div>
    </div>
  );
}

function VerificationTab({ d }: { d: Record<string, unknown> }) {
  const addr = d.address as Record<string, unknown> | undefined;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding={16}>
        <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 12px" }}>Business identity</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 10, fontSize: 13 }}>
          <Field label="Business Name" value={String(d.business_name ?? "—")} />
          <Field label="Owner" value={String(d.owner_name ?? "—")} />
          <Field label="Email" value={String(d.email ?? d.owner_email ?? "—")} />
          <Field label="Phone" value={String(d.phone ?? "—")} />
          <Field label="Registered Address" value={`${addr?.line1 ?? "—"}${addr?.city ? `, ${addr.city}` : ""}${addr?.state ? `, ${addr.state}` : ""}${addr?.zipcode ? ` - ${addr.zipcode}` : ""}`} />
          <Field label="GST Number" value={String(d.gst_number ?? "—")} />
        </div>
      </Card>
      <Card padding={16}>
        <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 12px" }}>Verification status</h3>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <Badge variant={d.verification_status === "approved" ? "success" : d.verification_status === "rejected" ? "danger" : "default"}>{String(d.verification_status)}</Badge>
          <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Registration: {String(d.registration_status)}</span>
        </div>
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 12 }}>
          Per-requirement checklist (document status, reviewer, expiry) and review actions (Start Review,
          Approve, Reject, Request Changes) live in the Onboarding Queue tab on the Providers workspace for
          providers still in review — not duplicated here to avoid two places that can approve the same
          provider.
        </p>
      </Card>
    </div>
  );
}

function FinanceTab({ providerId }: { providerId: string }) {
  const finance = useApi(useCallback(() => hsProviderDirectoryApi.getFinance(providerId), [providerId]));
  if (finance.loading) return <Skeleton height={300} />;
  if (finance.error) {
    return <Card padding={16}><p style={{ color: "var(--danger-text)" }}>Finance data unavailable: {finance.error}</p></Card>;
  }
  const f = finance.data as Record<string, unknown> | undefined;
  if (!f) return null;
  const deposit = f.security_deposit as Record<string, unknown> | undefined;
  const credits = f.usage_credits as Record<string, unknown> | undefined;
  const charges = (f.provider_charges ?? []) as Record<string, unknown>[];
  const topups = (f.topup_history ?? []) as Record<string, unknown>[];
  const paymentSetup = f.payment_setup as Record<string, unknown> | null | undefined;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding={12} style={{ background: "var(--surface-sunken)" }}>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>{String(f.customer_payment_note)}</p>
      </Card>

      {paymentSetup && (
        <Card padding={16}>
          <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 12px" }}>Payment & Invoicing Setup</h3>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 10px" }}>
            Chosen by the provider during Home Services onboarding.
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
            {paymentSetup.accepts_cash && <Badge variant="success">Accepts Cash</Badge>}
            {paymentSetup.accepts_upi && <Badge variant="success">Accepts UPI</Badge>}
            {paymentSetup.accepts_card_at_service_location && <Badge variant="success">Accepts Card On-Site</Badge>}
            {paymentSetup.accepts_bank_transfer && <Badge variant="success">Accepts Bank Transfer</Badge>}
            {!paymentSetup.accepts_cash && !paymentSetup.accepts_upi && !paymentSetup.accepts_card_at_service_location && !paymentSetup.accepts_bank_transfer && (
              <Badge variant="warning">No payment method configured</Badge>
            )}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, fontSize: 13 }}>
            <Field label="Payment Confirmation Required" value={paymentSetup.payment_confirmation_required ? "Yes" : "No"} />
            <Field label="Issues Customer Receipt" value={paymentSetup.issue_customer_receipt ? "Yes" : "No"} />
            <Field label="Invoice Business Name" value={String(paymentSetup.invoice_business_name ?? "—")} />
            <Field label="Invoice Prefix" value={String(paymentSetup.invoice_prefix ?? "—")} />
          </div>
        </Card>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
        <StatCard label="Usage Credit Balance" value={money(credits?.balance as string)} sub={credits?.low_balance ? "Low balance" : undefined} />
        <StatCard label="Security Deposit" value={String(deposit?.status ?? "not_required")} />
        <StatCard label="Deposit Required" value={money(deposit?.required_amount as string)} />
        <StatCard label="Deposit Held" value={money(deposit?.current_balance as string)} />
      </div>

      <div>
        <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 8px" }}>Provider charges</h3>
        <DataTable
          rows={charges}
          emptyText="No provider charges recorded for this provider yet."
          columns={[
            { key: "charge_model", label: "Model", render: v => <Badge>{String(v)}</Badge> },
            { key: "amount", label: "Amount", render: v => money(v as string) },
            { key: "status", label: "Status", render: v => <Badge variant={v === "posted" || v === "deducted" ? "success" : "default"}>{String(v)}</Badge> },
            { key: "triggered_at", label: "Triggered", render: v => dt(v as string) },
          ]}
        />
      </div>

      <div>
        <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 8px" }}>Top-up history</h3>
        <DataTable
          rows={topups}
          emptyText="No credit top-ups recorded for this provider yet."
          columns={[
            { key: "credits_purchased", label: "Credits" },
            { key: "amount_paid", label: "Amount Paid", render: v => money(v as string) },
            { key: "payment_status", label: "Status", render: v => <Badge variant={v === "credited" ? "success" : v === "failed" ? "danger" : "default"}>{String(v)}</Badge> },
            { key: "created_at", label: "Created", render: v => dt(v as string) },
          ]}
        />
      </div>
    </div>
  );
}

function QualityTab({ providerId }: { providerId: string }) {
  const quality = useApi(useCallback(() => hsProviderDirectoryApi.getQuality(providerId), [providerId]));
  const reviews = useApi(useCallback(() => hsReviewApi.getProviderReviewSummary("home-services", providerId), [providerId]));
  if (quality.loading) return <Skeleton height={300} />;
  if (quality.error) {
    return <Card padding={16}><p style={{ color: "var(--danger-text)" }}>Quality data unavailable: {quality.error}</p></Card>;
  }
  const q = quality.data as Record<string, unknown> | undefined;
  if (!q) return null;
  const complaints = (q.complaints ?? []) as Record<string, unknown>[];
  const rs = reviews.data?.summary as Record<string, unknown> | null | undefined;
  const recentReviews = (reviews.data?.recent_reviews ?? []) as Record<string, unknown>[];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
        <StatCard label="Average Rating" value={rs ? Number(rs.average_rating).toFixed(1) : "—"}
          sub={rs ? `${rs.total_reviews} reviews` : reviews.error ? "Unavailable" : reviews.loading ? "Loading…" : "No reviews yet"} />
        <StatCard label="Health Score" value={`${q.health_score}%`} sub={String(q.health_band)} />
        <StatCard label="Open Complaints" value={String(q.open_complaints_count ?? 0)} />
        <StatCard label="Total Complaints" value={String(q.total_complaints ?? 0)} />
        {reviews.data && (
          <>
            <StatCard label="Low-Rating Reviews" value={String(reviews.data.low_rating_count ?? 0)} />
            <StatCard label="Response Rate" value={`${reviews.data.provider_response_rate ?? 0}%`} />
            <StatCard label="Open Review Reports" value={String(reviews.data.open_review_reports ?? 0)} />
          </>
        )}
      </div>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
        Completion rate, cancellation rate, SLA adherence and repeat-customer rate aren&apos;t wired into
        this tab yet — they need canonical read services this page doesn&apos;t reach into.
      </p>
      {recentReviews.length > 0 && (
        <div>
          <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 8px" }}>Recent reviews</h3>
          {recentReviews.map(rv => (
            <a key={rv.id as string} href={`/admin/home-services/service-jobs/${rv.job_id}?tab=review`}
              style={{ display: "block", padding: "8px 0", borderBottom: "1px solid var(--border)", fontSize: 12, textDecoration: "none", color: "inherit" }}>
              <strong>{String(rv.overall_rating)}★</strong> — {String(rv.review_text ?? "").slice(0, 100) || "No written review"}
            </a>
          ))}
        </div>
      )}
      <div>
        <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 8px" }}>Complaints</h3>
        <DataTable
          rows={complaints}
          emptyText="No complaints recorded for this provider."
          columns={[
            { key: "complaint_number", label: "Complaint #" },
            { key: "title", label: "Title", render: v => v ? String(v) : "—" },
            { key: "severity", label: "Severity", render: v => <Badge variant={v === "high" || v === "critical" ? "danger" : v === "medium" ? "warning" : "default"}>{String(v ?? "—")}</Badge> },
            { key: "status", label: "Status", render: v => <Badge variant={v === "resolved" || v === "closed" ? "success" : "default"}>{String(v)}</Badge> },
            { key: "sla_status", label: "SLA", render: v => <Badge variant={v === "breached" ? "danger" : "success"}>{String(v ?? "—")}</Badge> },
            { key: "created_at", label: "Created", render: v => dt(v as string) },
          ]}
        />
      </div>
    </div>
  );
}

function TeamTab({ providerId }: { providerId: string }) {
  const team = useApi(useCallback(() => hsProviderDirectoryApi.getTeam(providerId), [providerId]));
  if (team.loading) return <Skeleton height={300} />;
  if (team.error) return <Card padding={16}><p style={{ color: "var(--danger-text)" }}>Team data unavailable: {team.error}</p></Card>;
  const t = team.data as Record<string, unknown> | undefined;
  if (!t) return null;
  const staff = (t.staff ?? []) as Record<string, unknown>[];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12 }}>
        <StatCard label="Total Staff" value={String(t.total_staff ?? 0)} />
        <StatCard label="Verified" value={String(t.verified_staff ?? 0)} />
        <StatCard label="Available" value={String(t.available_staff ?? 0)} />
        <StatCard label="Capability Incomplete" value={String(t.capability_incomplete_staff ?? 0)} />
        <StatCard label="Suspended" value={String(t.suspended_staff ?? 0)} />
      </div>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
        Only staff explicitly assigned to this provider&apos;s Home Services operation appear here — a
        multi-vertical tenant&apos;s staff do not automatically show up in this list.
      </p>
      <DataTable
        rows={staff}
        emptyText="No staff explicitly assigned to Home Services for this provider yet."
        columns={[
          { key: "name", label: "Staff Member", render: v => v ? String(v) : "—" },
          { key: "designation", label: "Designation", render: v => v ? String(v) : "—" },
          { key: "verification_status", label: "Verification", render: v => <Badge variant={v === "verified" ? "success" : "default"}>{String(v)}</Badge> },
          { key: "availability_status", label: "Availability", render: v => <Badge variant={v === "available" ? "success" : "default"}>{String(v)}</Badge> },
          { key: "assignment_status", label: "Assignment", render: v => <Badge variant={v === "suspended" ? "danger" : "default"}>{String(v)}</Badge> },
        ]}
      />
    </div>
  );
}

function OperationsTab({ providerId }: { providerId: string }) {
  const ops = useApi(useCallback(() => hsProviderDirectoryApi.getOperations(providerId), [providerId]));
  if (ops.loading) return <Skeleton height={300} />;
  if (ops.error) return <Card padding={16}><p style={{ color: "var(--danger-text)" }}>Operations data unavailable: {ops.error}</p></Card>;
  const o = ops.data as Record<string, unknown> | undefined;
  if (!o) return null;
  const jobs = (o.jobs ?? []) as Record<string, unknown>[];
  const byStatus = (o.by_status ?? {}) as Record<string, number>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12 }}>
        <StatCard label="Total Jobs" value={String(o.total_jobs ?? 0)} />
        <StatCard label="Active Jobs" value={String(o.active_jobs ?? 0)} />
        {Object.entries(byStatus).map(([status, count]) => (
          <StatCard key={status} label={status.replace(/_/g, " ")} value={String(count)} />
        ))}
      </div>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
        Quotes/checklists, SLA event detail and cancellation reasons aren&apos;t wired into this tab yet.
      </p>
      <DataTable
        rows={jobs}
        emptyText="No Home Services jobs recorded for this provider yet."
        columns={[
          { key: "job_number", label: "Job #" },
          { key: "status", label: "Status", render: v => <Badge variant={v === "completed" ? "success" : v === "cancelled" ? "danger" : "default"}>{String(v)}</Badge> },
          { key: "assignment_status", label: "Assignment", render: v => v ? String(v) : "—" },
          { key: "updated_at", label: "Last Update", render: v => dt(v as string) },
        ]}
      />
    </div>
  );
}

function ActivityTab({ providerId }: { providerId: string }) {
  const activity = useApi(useCallback(() => hsProviderDirectoryApi.getActivity(providerId), [providerId]));
  if (activity.loading) return <Skeleton height={300} />;
  if (activity.error) return <Card padding={16}><p style={{ color: "var(--danger-text)" }}>Activity data unavailable: {activity.error}</p></Card>;
  const a = activity.data as Record<string, unknown> | undefined;
  if (!a) return null;
  const events = (a.events ?? []) as Record<string, unknown>[];
  const documents = (a.documents ?? []) as Record<string, unknown>[];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding={14}>
        <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>Documents</h3>
        <DataTable
          rows={documents}
          emptyText="No documents uploaded for this provider yet."
          columns={[
            { key: "doc_type", label: "Type", render: v => String(v).replace(/_/g, " ") },
            { key: "label", label: "Label", render: v => v ? String(v) : "—" },
            { key: "document_number", label: "Number", render: v => v ? String(v) : "—" },
            { key: "status", label: "Status", render: v => <Badge variant={v === "verified" ? "success" : v === "rejected" ? "danger" : "default"}>{String(v)}</Badge> },
            { key: "expiry_date", label: "Expires", render: v => v ? dt(v as string) : "—" },
            { key: "media_asset_id", label: "Attachment", render: (v, row) => v ? (
              <button
                onClick={async e => {
                  e.stopPropagation();
                  try {
                    // The signed-preview-url flow (mediaAdminApi.createSignedPreviewUrl)
                    // still requires an Authorization header to resolve
                    // (its own "unauthenticated" comment doesn't match its
                    // actual implementation) -- window.open() can't carry
                    // that header, so it always 401s. Fetching the file
                    // directly with the header and opening it as a blob
                    // sidesteps that broken layer entirely.
                    const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
                    const token = localStorage.getItem("serviceos_admin_token") ?? "";
                    const res = await fetch(`${API_BASE}/v1/media/${v}/view`, { headers: { Authorization: `Bearer ${token}` } });
                    if (!res.ok) throw new Error(String(res.status));
                    const blob = await res.blob();
                    window.open(URL.createObjectURL(blob), "_blank");
                  } catch {
                    alert("Could not open this attachment.");
                  }
                }}
                style={{ background: "none", border: "none", color: "var(--brand)", cursor: "pointer", padding: 0, fontSize: 13, textDecoration: "underline" }}>
                View
              </button>
            ) : <span style={{ color: "var(--text-tertiary)" }}>No file</span> },
          ]}
        />
      </Card>
      <div>
        <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 8px" }}>Audit timeline</h3>
        <DataTable
          rows={events}
          emptyText="No audit events recorded for this provider."
          columns={[
            { key: "operation", label: "Action" },
            { key: "engine_id", label: "Source" },
            { key: "actor_role", label: "Actor", render: v => v ? String(v) : "—" },
            { key: "created_at", label: "When", render: v => dt(v as string) },
          ]}
        />
      </div>
    </div>
  );
}

function ServicesTab({ providerId }: { providerId: string }) {
  const services = useApi(useCallback(() => hsProviderDirectoryApi.getServices(providerId), [providerId]));
  if (services.loading) return <Skeleton height={300} />;
  if (services.error) return <Card padding={16}><p style={{ color: "var(--danger-text)" }}>Services data unavailable: {services.error}</p></Card>;
  const s = services.data as Record<string, unknown> | undefined;
  if (!s) return null;
  const rows = (s.services ?? []) as Record<string, unknown>[];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
        <StatCard label="Total Services" value={String(s.total_services ?? 0)} />
        <StatCard label="Published" value={String(s.published_services ?? 0)} />
        <StatCard label="Active" value={String(s.active_services ?? 0)} />
        <StatCard label="Price Configured" value={String(s.price_configured_count ?? 0)} />
        <StatCard label="Missing Price Config" value={String(s.missing_price_config_count ?? 0)} />
      </div>
      <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0, fontWeight: 600 }}>
        Pricing ownership: Tenant-owned
      </p>
      <DataTable
        rows={rows}
        emptyText="No Home Services service setup found for this provider yet."
        columns={[
          { key: "master_service_name", label: "Master Service", render: v => v ? String(v) : "—" },
          { key: "job_type", label: "Job Type" },
          { key: "setup_status", label: "Setup", render: v => <Badge variant={v === "published" ? "success" : "default"}>{String(v)}</Badge> },
          { key: "published", label: "Published", render: v => v ? <Badge variant="success">Yes</Badge> : <Badge>No</Badge> },
          { key: "requires_brand", label: "Brand Required", render: v => v ? "Yes" : "No" },
          { key: "requires_type", label: "Type Required", render: v => v ? "Yes" : "No" },
          { key: "price_configured", label: "Pricing", render: v => v ? <Badge variant="success">Configured</Badge> : <Badge variant="warning">Missing</Badge> },
        ]}
      />
      <Card padding={14}>
        <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>Coverage ({String(s.total_coverage_areas ?? 0)})</h3>
        <DataTable
          rows={(s.coverage_areas ?? []) as Record<string, unknown>[]}
          emptyText="No active serviceable areas configured for this provider yet."
          columns={[
            { key: "coverage_type", label: "Type" },
            { key: "city", label: "City", render: v => v ? String(v) : "—" },
            { key: "zipcode", label: "Zipcode", render: v => v ? String(v) : "—" },
            { key: "status", label: "Status", render: v => <Badge variant={v === "ACTIVE" ? "success" : "default"}>{String(v)}</Badge> },
          ]}
        />
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "10px 0 0" }}>
          Admin does not create city, zipcode or tier configurations from this page — coverage is provider-submitted and shown read-only here.
        </p>
      </Card>
    </div>
  );
}

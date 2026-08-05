"use client";
import React, { useCallback, useState } from "react";
import { useParams } from "next/navigation";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, SectionHeader, DataTable, Modal, Input } from "../../../../components/shared/ui";
import { adminCustomersApi, AdminCustomer } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { ArrowLeft, ExternalLink, X } from "lucide-react";
import Link from "next/link";

const HEALTH_BADGE: Record<string, "success" | "warning" | "danger" | "info" | "muted"> = {
  new: "muted", healthy: "success", active: "info",
  at_risk: "warning", dormant: "muted", complaint_risk: "danger", blocked: "danger",
};

const STATUS_BADGE: Record<string, "success" | "warning" | "danger" | "info" | "muted"> = {
  completed: "success", confirmed: "info", in_progress: "info",
  pending_confirmation: "warning", cancelled: "danger", void: "muted",
};

type Tab = "overview" | "bookings" | "complaints" | "credits" | "addresses" | "sessions" | "privacy";

function InfoRow({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div style={{ display: "flex", gap: 12, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
      <div style={{ width: 140, fontSize: 12, color: "var(--muted-text)", flexShrink: 0 }}>{label}</div>
      <div style={{ fontSize: 13, color: "var(--text)", fontWeight: 500 }}>{value ?? "—"}</div>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return <p style={{ padding: "28px 20px", textAlign: "center", color: "var(--muted-text)", fontSize: 13 }}>{text}</p>;
}

// Reusable content -- used both by the standalone /admin/customers/[id]
// route (default export below) and as an in-place drawer from the
// customers list page (no navigation away, matching the pattern used on
// Home Services Customers). `onClose` is only set in the drawer case.
function CustomerDetailContent({ customerId, onClose }: { customerId: string; onClose?: () => void }) {
  const [tab, setTab] = useState<Tab>("overview");
  const [reasonModal, setReasonModal] = useState<null | "block" | "unblock" | "suspend" | "reactivate" | "revoke_sessions">(null);
  const [reason, setReason] = useState("");
  const [creditModal, setCreditModal] = useState(false);
  const [creditAmount, setCreditAmount] = useState("");
  const [creditReason, setCreditReason] = useState("");

  const customerFetch = useApi(
    useCallback(() => adminCustomersApi.get(customerId), [customerId]), [customerId],
  );
  const customer: AdminCustomer | null =
    (customerFetch.data as { data?: AdminCustomer } | null)?.data ?? null;

  const bookingsFetch = useApi(
    useCallback(() => adminCustomersApi.bookings(customerId, { page: 1 }), [customerId]), [customerId],
  );
  type BookingRow = { id: string; booking_number: string; tenant_name: string; category_name: string; status: string; amount: number | null; city: string; created_at: string | null };
  type BookingsData = { bookings: BookingRow[]; meta: { page: number; total: number; total_pages: number } };
  const bookingsData: BookingsData | undefined =
    (bookingsFetch.data as unknown as { data?: BookingsData } | null)?.data;
  const bookings = bookingsData?.bookings ?? [];
  const bookingsMeta = bookingsData?.meta;

  const complaintsFetch = useApi(useCallback(() => adminCustomersApi.complaints(customerId), [customerId]), [customerId]);
  const complaints = (complaintsFetch.data as unknown as { data?: { complaints: any[] } } | null)?.data?.complaints ?? [];

  const creditsFetch = useApi(useCallback(() => adminCustomersApi.serviceCredits(customerId), [customerId]), [customerId]);
  const creditsData = (creditsFetch.data as unknown as { data?: { credits: any[]; summary: any } } | null)?.data;

  const addressesFetch = useApi(useCallback(() => adminCustomersApi.addresses(customerId), [customerId]), [customerId]);
  const addresses = (addressesFetch.data as unknown as { data?: { addresses: any[] } } | null)?.data?.addresses ?? [];

  const sessionsFetch = useApi(useCallback(() => adminCustomersApi.sessions(customerId), [customerId]), [customerId]);
  const sessions = (sessionsFetch.data as unknown as { data?: { sessions: any[] } } | null)?.data?.sessions ?? [];

  const loginHistoryFetch = useApi(useCallback(() => adminCustomersApi.loginHistory(customerId), [customerId]), [customerId]);
  const loginHistory = (loginHistoryFetch.data as unknown as { data?: { login_history: any[] } } | null)?.data?.login_history ?? [];

  const privacyFetch = useApi(useCallback(() => adminCustomersApi.privacyRequests(customerId), [customerId]), [customerId]);
  const privacyRequests = (privacyFetch.data as unknown as { data?: { items: any[] } } | null)?.data?.items ?? [];

  const blockAction = useAction(useCallback((r: string) => adminCustomersApi.block(customerId, r), [customerId]));
  const unblockAction = useAction(useCallback((r: string) => adminCustomersApi.unblock(customerId, r), [customerId]));
  const suspendAction = useAction(useCallback((r: string) => adminCustomersApi.suspend(customerId, r), [customerId]));
  const reactivateAction = useAction(useCallback((r: string) => adminCustomersApi.reactivate(customerId, r), [customerId]));
  const revokeSessionsAction = useAction(useCallback((r: string) => adminCustomersApi.revokeAllSessions(customerId, r), [customerId]));
  const issueCreditAction = useAction(useCallback(
    (amount: number, issued_reason: string) => adminCustomersApi.issueServiceCredit(customerId, { amount, issued_reason }),
    [customerId]));

  async function confirmReasonAction() {
    if (!reasonModal || !reason) return;
    const map = { block: blockAction, unblock: unblockAction, suspend: suspendAction,
      reactivate: reactivateAction, revoke_sessions: revokeSessionsAction };
    const result = await map[reasonModal].execute(reason);
    if (result) {
      setReasonModal(null); setReason("");
      customerFetch.refetch(); sessionsFetch.refetch();
    }
  }

  async function handleIssueCredit() {
    const amt = parseFloat(creditAmount);
    if (!amt || !creditReason) return;
    const result = await issueCreditAction.execute(amt, creditReason);
    if (result) { setCreditModal(false); setCreditAmount(""); setCreditReason(""); creditsFetch.refetch(); }
  }

  const bookingColumns = [
    {
      key: "booking_number", label: "Booking #", width: 130,
      render: (_: unknown, row: BookingRow) => (
        <Link href={`/admin/bookings/${row.id}`}
          style={{ fontFamily: "monospace", fontSize: 12, color: "var(--primary)", textDecoration: "none", fontWeight: 600 }}>
          {row.booking_number}
        </Link>
      ),
    },
    {
      key: "tenant_name", label: "Provider",
      render: (_: unknown, row: BookingRow) => <span style={{ fontSize: 13 }}>{row.tenant_name || "—"}</span>,
    },
    {
      key: "category_name", label: "Service",
      render: (_: unknown, row: BookingRow) => <span style={{ fontSize: 12 }}>{row.category_name || "—"}</span>,
    },
    {
      key: "status", label: "Status", width: 150,
      render: (_: unknown, row: BookingRow) => (
        <Badge variant={STATUS_BADGE[row.status] ?? "muted"}>{row.status.replace(/_/g, " ")}</Badge>
      ),
    },
    {
      key: "amount", label: "Amount", width: 90,
      render: (_: unknown, row: BookingRow) => (
        <span style={{ fontFamily: "monospace", fontSize: 13 }}>
          {row.amount != null ? `₹${row.amount.toFixed(0)}` : "—"}
        </span>
      ),
    },
    {
      key: "created_at", label: "Date", width: 100,
      render: (_: unknown, row: BookingRow) => {
        const d = row.created_at ? new Date(row.created_at) : null;
        return <span style={{ fontSize: 12, color: "var(--muted-text)" }}>{d ? d.toLocaleDateString("en-IN") : "—"}</span>;
      },
    },
    {
      key: "id", label: "", width: 36,
      render: (_: unknown, row: BookingRow) => (
        <Link href={`/admin/bookings/${row.id}`} style={{ color: "var(--muted-text)" }}>
          <ExternalLink size={14} />
        </Link>
      ),
    },
  ];

  const tabStyle = (t: Tab): React.CSSProperties => ({
    padding: "8px 18px", border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600,
    borderBottom: `2px solid ${tab === t ? "var(--primary)" : "transparent"}`,
    color: tab === t ? "var(--primary)" : "var(--muted-text)",
    background: "transparent", whiteSpace: "nowrap",
  });

  const isBlocked = customer && !customer.is_active;

  return (
    <>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
        {onClose ? (
          <button onClick={onClose} style={{ color: "var(--muted-text)", display: "flex", alignItems: "center", gap: 4,
            fontSize: 13, background: "none", border: "none", cursor: "pointer", padding: 0 }}>
            <X size={15} /> Close
          </button>
        ) : (
          <Link href="/admin/customers" style={{ color: "var(--muted-text)", display: "flex", alignItems: "center", gap: 4, fontSize: 13, textDecoration: "none" }}>
            <ArrowLeft size={15} /> Customers
          </Link>
        )}
      </div>

      <SectionHeader
        title={customerFetch.loading ? "Loading…" : (customer?.full_name ?? "Customer")}
        subtitle={customer ? `Customer ID: ${customerId}` : ""}
        actions={customer ? (
          <div style={{ display: "flex", gap: 8 }}>
            {isBlocked
              ? <Btn variant="secondary" size="sm" onClick={() => setReasonModal("unblock")}>Unblock</Btn>
              : <Btn variant="danger" size="sm" onClick={() => setReasonModal("block")}>Block</Btn>}
            <Btn variant="secondary" size="sm" onClick={() => setReasonModal("suspend")}>Suspend</Btn>
            <Btn variant="secondary" size="sm" onClick={() => setReasonModal("reactivate")}>Reactivate</Btn>
            <Btn variant="danger" size="sm" onClick={() => setReasonModal("revoke_sessions")}>Force Logout</Btn>
          </div>
        ) : undefined}
      />

      {customerFetch.error ? (
        <Card padding={32} style={{ textAlign: "center" }}>
          <p style={{ color: "var(--danger-text,#b91c1c)", fontSize: 14, fontWeight: 600, margin: "0 0 4px" }}>
            Could not load customer.
          </p>
          <p style={{ color: "var(--muted-text)", fontSize: 13, margin: "0 0 4px" }}>{customerFetch.error}</p>
          {customerFetch.requestId && (
            <p style={{ fontSize: 11, color: "var(--muted-text)", margin: "0 0 14px", fontFamily: "monospace" }}>
              Request ID: {customerFetch.requestId}
            </p>
          )}
          <Btn variant="secondary" size="sm" onClick={() => customerFetch.refetch()} style={{ marginTop: 12 }}>
            Retry
          </Btn>
        </Card>
      ) : customerFetch.loading ? (
        <Card padding={32}><div style={{ color: "var(--muted-text)", fontSize: 13 }}>Loading customer…</div></Card>
      ) : customer ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Quick stats row */}
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {[
              { label: "Health", value: <Badge variant={HEALTH_BADGE[customer.health_band] ?? "muted"}>{customer.health_band.replace(/_/g, " ")}</Badge> },
              { label: "Total Bookings", value: customer.total_bookings },
              { label: "Completed", value: customer.completed_bookings },
              { label: "Cancelled", value: customer.cancelled_bookings },
              { label: "Complaints", value: customer.complaints_count },
              { label: "Avg Rating", value: customer.average_rating != null ? `★ ${customer.average_rating.toFixed(1)}` : "—" },
              { label: "Providers", value: customer.tenant_count },
            ].map(({ label, value }) => (
              <div key={label} style={{
                background: "var(--card-bg)", border: "1px solid var(--border)", borderRadius:"var(--radius-md)",
                padding: "12px 16px", flex: 1, minWidth: 90,
              }}>
                <div style={{ fontSize: 11, color: "var(--muted-text)", marginBottom: 4 }}>{label}</div>
                <div style={{ fontSize: 15, fontWeight: 700 }}>{value}</div>
              </div>
            ))}
          </div>

          {/* Tabs */}
          <Card padding={0}>
            <div style={{ display: "flex", borderBottom: "1px solid var(--border)", padding: "0 8px", overflowX: "auto" }}>
              <button style={tabStyle("overview")} onClick={() => setTab("overview")}>Overview</button>
              <button style={tabStyle("bookings")} onClick={() => setTab("bookings")}>
                Bookings {bookingsMeta?.total != null ? `(${bookingsMeta.total})` : ""}
              </button>
              <button style={tabStyle("complaints")} onClick={() => setTab("complaints")}>
                Complaints & Disputes {complaints.length ? `(${complaints.length})` : ""}
              </button>
              <button style={tabStyle("credits")} onClick={() => setTab("credits")}>Service Credits</button>
              <button style={tabStyle("addresses")} onClick={() => setTab("addresses")}>Addresses</button>
              <button style={tabStyle("sessions")} onClick={() => setTab("sessions")}>Sessions & Login History</button>
              <button style={tabStyle("privacy")} onClick={() => setTab("privacy")}>Privacy / DPDP</button>
            </div>

            {tab === "overview" && (
              <div style={{ padding: 20 }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 32 }}>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: "var(--muted-text)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>
                      Contact Details
                    </div>
                    <InfoRow label="Full Name" value={customer.full_name} />
                    <InfoRow label="Phone" value={customer.phone} />
                    <InfoRow label="Email" value={customer.email} />
                    <InfoRow label="Status" value={customer.is_active ? "Active" : "Blocked/Inactive"} />
                    <InfoRow label="Member Since" value={customer.created_at ? new Date(customer.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" }) : undefined} />
                  </div>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: "var(--muted-text)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>
                      Location
                    </div>
                    <InfoRow label="City" value={customer.city} />
                    <InfoRow label="District" value={customer.district} />
                    <InfoRow label="State" value={customer.state} />
                    <InfoRow label="Zipcode" value={customer.zipcode} />
                    <InfoRow label="Last Provider" value={customer.last_tenant_name} />
                    <InfoRow label="Last Booking" value={customer.last_booking_at ? new Date(customer.last_booking_at).toLocaleDateString("en-IN") : undefined} />
                  </div>
                </div>
              </div>
            )}

            {tab === "bookings" && (
              <div style={{ padding: 0 }}>
                <DataTable
                  columns={bookingColumns as unknown as Parameters<typeof DataTable>[0]["columns"]}
                  rows={bookings as unknown as Record<string, unknown>[]}
                  loading={bookingsFetch.loading}
                  emptyText="No bookings found for this customer."
                />
                {bookingsMeta && bookingsMeta.total_pages > 1 && (
                  <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)", textAlign: "center", color: "var(--muted-text)", fontSize: 12 }}>
                    Showing page 1 of {bookingsMeta.total_pages} ({bookingsMeta.total} total bookings)
                  </div>
                )}
              </div>
            )}

            {tab === "complaints" && (
              <div style={{ padding: complaints.length ? 0 : 20 }}>
                {complaintsFetch.loading ? <EmptyState text="Loading…" /> : complaints.length === 0 ? (
                  <EmptyState text="No complaints or disputes for this customer." />
                ) : complaints.map((c: any) => (
                  <div key={c.id} style={{ padding: "12px 20px", borderBottom: "1px solid var(--border)" }}>
                    <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 4 }}>
                      <span style={{ fontWeight: 600, fontSize: 13 }}>{c.complaint_number}</span>
                      <Badge variant={c.status === "open" ? "danger" : c.status === "resolved" ? "success" : "muted"} size="sm">{c.status}</Badge>
                      <Badge variant="muted" size="sm">{c.priority}</Badge>
                      {c.settlement_status && <Badge variant="info" size="sm">{c.settlement_status}</Badge>}
                    </div>
                    <p style={{ fontSize: 12, color: "var(--muted-text)", margin: 0 }}>{c.description}</p>
                  </div>
                ))}
              </div>
            )}

            {tab === "credits" && (
              <div style={{ padding: 20 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                  {creditsData?.summary && (
                    <div style={{ display: "flex", gap: 20, fontSize: 13 }}>
                      <span><strong>{creditsData.summary.active_credits}</strong> active</span>
                      <span>Balance: <strong>₹{creditsData.summary.active_credit_balance.toFixed(2)}</strong></span>
                    </div>
                  )}
                  <Btn variant="primary" size="sm" onClick={() => setCreditModal(true)}>Issue Service Credit</Btn>
                </div>
                {creditsFetch.loading ? <EmptyState text="Loading…" /> : (creditsData?.credits.length ?? 0) === 0 ? (
                  <EmptyState text="No service credits issued to this customer." />
                ) : creditsData!.credits.map((c: any) => (
                  <div key={c.id} style={{ display: "flex", gap: 12, alignItems: "center", padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{c.credit_number}</span>
                    <Badge variant={c.status === "active" ? "success" : "muted"} size="sm">{c.status}</Badge>
                    <span style={{ fontSize: 12, color: "var(--muted-text)", flex: 1 }}>{c.issued_reason}</span>
                    <span style={{ fontFamily: "monospace", fontSize: 13 }}>₹{c.remaining_amount} / ₹{c.amount}</span>
                  </div>
                ))}
              </div>
            )}

            {tab === "addresses" && (
              <div style={{ padding: 20 }}>
                {addressesFetch.loading ? <EmptyState text="Loading…" /> : addresses.length === 0 ? (
                  <EmptyState text="No saved addresses for this customer." />
                ) : addresses.map((a: any) => (
                  <div key={a.id} style={{ display: "flex", gap: 10, alignItems: "flex-start", padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
                    <div style={{ flex: 1 }}>
                      <p style={{ margin: 0, fontSize: 13 }}>{a.address_line_1}{a.address_line_2 ? `, ${a.address_line_2}` : ""}</p>
                      <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--muted-text)" }}>{a.city}, {a.state} {a.zipcode}</p>
                    </div>
                    {a.is_default && <Badge variant="info" size="sm">Default</Badge>}
                  </div>
                ))}
              </div>
            )}

            {tab === "sessions" && (
              <div style={{ padding: 20 }}>
                <h4 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>Active Sessions</h4>
                {sessionsFetch.loading ? <EmptyState text="Loading…" /> : sessions.length === 0 ? (
                  <EmptyState text="No sessions found." />
                ) : sessions.map((s: any) => (
                  <div key={s.session_id} style={{ display: "flex", gap: 10, alignItems: "center", padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                    <span style={{ fontSize: 13, flex: 1 }}>{s.device_name}</span>
                    <span style={{ fontSize: 12, color: "var(--muted-text)" }}>{s.ip_address ?? "—"}</span>
                    <Badge variant={s.status === "active" ? "success" : "muted"} size="sm">{s.status}</Badge>
                  </div>
                ))}
                <h4 style={{ fontSize: 13, fontWeight: 700, margin: "20px 0 10px" }}>Login History</h4>
                {loginHistoryFetch.loading ? <EmptyState text="Loading…" /> : loginHistory.length === 0 ? (
                  <EmptyState text="No login history recorded." />
                ) : loginHistory.map((e: any, i: number) => (
                  <div key={i} style={{ display: "flex", gap: 10, alignItems: "center", padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                    <Badge variant={e.event_type.includes("fail") ? "danger" : "success"} size="sm">{e.event_type}</Badge>
                    <span style={{ fontSize: 12, color: "var(--muted-text)", flex: 1 }}>{e.ip_address ?? "—"} {e.failure_reason ? `— ${e.failure_reason}` : ""}</span>
                    <span style={{ fontSize: 11, color: "var(--muted-text)" }}>{new Date(e.created_at).toLocaleString("en-IN")}</span>
                  </div>
                ))}
              </div>
            )}

            {tab === "privacy" && (
              <div style={{ padding: 20 }}>
                {privacyFetch.loading ? <EmptyState text="Loading…" /> : privacyRequests.length === 0 ? (
                  <EmptyState text="No DPDP/privacy requests for this customer." />
                ) : privacyRequests.map((p: any) => (
                  <div key={p.id} style={{ display: "flex", gap: 10, alignItems: "center", padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                    <span style={{ fontSize: 13, flex: 1 }}>{p.request_number} — {p.request_type.replace(/_/g, " ")}</span>
                    <Badge variant={p.sla_overdue ? "danger" : "muted"} size="sm">{p.status}</Badge>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      ) : null}

      <Modal open={!!reasonModal} onClose={() => setReasonModal(null)} title={
        reasonModal === "block" ? "Block Customer" : reasonModal === "unblock" ? "Unblock Customer"
        : reasonModal === "suspend" ? "Suspend Customer" : reasonModal === "reactivate" ? "Reactivate Customer"
        : "Force Logout Customer"
      }>
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Input label="Reason (required)" placeholder="Why is this action being taken?" value={reason} onChange={setReason} required />
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setReasonModal(null)}>Cancel</Btn>
            <Btn variant="danger" size="sm" disabled={!reason} onClick={confirmReasonAction}>Confirm</Btn>
          </div>
        </div>
      </Modal>

      <Modal open={creditModal} onClose={() => setCreditModal(false)} title="Issue Service Credit">
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Input label="Amount (₹)" placeholder="500" value={creditAmount} onChange={setCreditAmount} required />
          <Input label="Reason (required)" placeholder="Why is this credit being issued?" value={creditReason} onChange={setCreditReason} required />
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setCreditModal(false)}>Cancel</Btn>
            <Btn variant="primary" size="sm" disabled={!creditAmount || !creditReason} onClick={handleIssueCredit}>Issue Credit</Btn>
          </div>
        </div>
      </Modal>
    </>
  );
}

// Standalone route -- deep links (/admin/customers/[id]) still work directly.
export default function CustomerDetailPage() {
  const params = useParams<{ id: string }>();
  const customerId = params?.id ?? "";
  return (
    <AdminLayout activeNav="customers">
      <CustomerDetailContent customerId={customerId} />
    </AdminLayout>
  );
}

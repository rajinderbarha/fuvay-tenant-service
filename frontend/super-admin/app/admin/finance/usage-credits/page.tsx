"use client";
import { Suspense, useCallback, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, SectionHeader, Input, Skeleton } from "../../../../components/shared/ui";
import { RequirePermission, ReadOnlyNotice } from "../../../../components/shared/PermissionGate";
import { usePermissions } from "../../../../hooks/usePermissions";
import { usageCreditsAdminApi } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";

const DEMO_TENANT_ID = "34b427a7-b2be-496c-b826-6d51bb181248";

// FINAL-L5-03: useSearchParams() requires a Suspense boundary in the App
// Router for static export to succeed -- this page previously failed
// `next build` outright ("useSearchParams() should be wrapped in a suspense
// boundary"). Real, pre-existing build failure, not introduced this sprint.
export default function AdminUsageCreditsPage() {
  return (
    <Suspense fallback={<AdminLayout activeNav="finance-usage-credits"><Skeleton height={400}/></AdminLayout>}>
      <AdminUsageCreditsPageInner/>
    </Suspense>
  );
}

function AdminUsageCreditsPageInner() {
  const searchParams = useSearchParams();
  const perm = usePermissions();
  const jobIdFilter = searchParams.get("job_id") ?? "";
  const [tenantId, setTenantId] = useState(searchParams.get("tenant_id") || DEMO_TENANT_ID);
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");

  const ledger = useApi(useCallback(
    () => usageCreditsAdminApi.getTenantLedger(tenantId, jobIdFilter || undefined),
    [tenantId, jobIdFilter],
  ));

  const addAction = useAction(
    useCallback(() => usageCreditsAdminApi.addCredits(tenantId, Number(amount), reason), [tenantId, amount, reason]),
  );

  async function handleAddCredits() {
    const result = await addAction.execute();
    if (result) { setAmount(""); setReason(""); ledger.refetch(); }
  }

  const entries = ledger.data?.entries ?? [];
  const deductions = entries.filter(e => e.event_type === "completed_job_deduction");
  const totalDeducted = deductions.reduce((sum, e) => sum + Math.abs(e.credit_delta), 0);
  const currentBalance = entries[0]?.balance_after;

  return (
    <AdminLayout activeNav="finance-usage-credits">
      <RequirePermission requiredPermission="finance.usage_credits.read" parentLabel="Dashboard">
      <SectionHeader
        title="Usage Credits"
        subtitle={jobIdFilter
          ? `Filtered to the exact Completed Job Deduction ledger entry for job ${jobIdFilter.slice(0, 8)}…`
          : "Completed Job Deductions and usage credit ledger activity across tenants."}
      />

      {jobIdFilter && (
        <Card style={{ marginBottom: 16, background: "var(--info-bg)", border: "1px solid var(--info-border)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <p style={{ fontSize: 12, color: "var(--info-text)", margin: 0 }}>
              Filtered by job: <strong>{jobIdFilter}</strong>
            </p>
            <Link href="/admin/finance/usage-credits" style={{ fontSize: 12, color: "var(--info-text)" }}>Clear filter</Link>
          </div>
        </Card>
      )}

      <Card style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", gap: 10, alignItems: "flex-end" }}>
          <Input label="Tenant ID" value={tenantId} onChange={setTenantId} />
          <Btn size="sm" variant="secondary" onClick={() => ledger.refetch()}>Load Ledger</Btn>
        </div>
      </Card>

      {ledger.error && (
        <Card style={{ marginBottom: 20 }}>
          <p style={{ color: "var(--danger-text)", fontSize: 13 }}>
            Completed job deductions could not be loaded. Retry or contact support with request ID.
            {ledger.requestId && ` Request ID: ${ledger.requestId}`}
          </p>
        </Card>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 20 }}>
        <MiniStat label="Ledger Entries" value={entries.length} />
        <MiniStat label="Total Usage Credits Deducted" value={totalDeducted} />
        <MiniStat label="Current Balance (from ledger)" value={currentBalance ?? "—"} />
      </div>

      {perm.has("finance.usage_credits.adjust") ? (
      <Card style={{ marginBottom: 20 }}>
        <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>Add Usage Credits</p>
        <div style={{ display: "flex", gap: 10, alignItems: "flex-end" }}>
          <Input label="Amount" value={amount} onChange={setAmount} />
          <Input label="Reason" value={reason} onChange={setReason} />
          <Btn size="sm" variant="primary" loading={addAction.loading}
            disabled={!amount || !reason}
            onClick={handleAddCredits}>
            Add Credits
          </Btn>
        </div>
        {addAction.error && (
          <p style={{ fontSize: 12, color: "var(--danger-text)", marginTop: 8 }}>
            {addAction.error}{addAction.requestId && ` — Request ID: ${addAction.requestId}`}
          </p>
        )}
      </Card>
      ) : (
        <ReadOnlyNotice/>
      )}

      <Card padding={0}>
        <p style={{ fontSize: 13, fontWeight: 700, padding: "14px 16px 0" }}>Completed Job Deductions / Ledger</p>
        {ledger.loading ? (
          <div style={{ padding: 20, fontSize: 13, color: "var(--text-tertiary)" }}>Loading…</div>
        ) : entries.length === 0 ? (
          <div style={{ padding: 32, textAlign: "center", fontSize: 13, color: "var(--text-tertiary)" }}>
            No ledger entries for this tenant yet.
          </div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                {["Date", "Job ID", "Event Type", "Credit Change", "Balance Before", "Balance After", "Source", "Request ID"].map(h => (
                  <th key={h} style={{ textAlign: "left", padding: "10px 16px", fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {entries.map(e => (
                <tr key={e.ledger_id} style={{ borderBottom: "1px solid var(--border-subtle, var(--border))" }}>
                  <td style={{ padding: "10px 16px" }}>{new Date(e.created_at).toLocaleDateString()}</td>
                  <td style={{ padding: "10px 16px" }}>{e.job_id ? e.job_id.slice(0, 8) : "—"}</td>
                  <td style={{ padding: "10px 16px" }}>
                    <Badge variant={e.event_type === "completed_job_deduction" ? "warning" : "info"} size="sm">
                      {e.event_type === "completed_job_deduction" ? "Completed Job Deduction" : e.event_type}
                    </Badge>
                  </td>
                  <td style={{ padding: "10px 16px", fontWeight: 700, color: e.credit_delta < 0 ? "var(--danger-text)" : "var(--success-text)" }}>
                    {e.credit_delta > 0 ? "+" : ""}{e.credit_delta}
                  </td>
                  <td style={{ padding: "10px 16px" }}>{e.balance_before}</td>
                  <td style={{ padding: "10px 16px" }}>{e.balance_after}</td>
                  <td style={{ padding: "10px 16px", fontSize: 11, color: "var(--text-tertiary)" }}>{e.deduction_source ? e.deduction_source.slice(0, 8) : "—"}</td>
                  <td style={{ padding: "10px 16px", fontSize: 11, color: "var(--text-tertiary)" }}>{e.request_id ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
      </RequirePermission>
    </AdminLayout>
  );
}

function MiniStat({ label, value }: { label: string; value: number | string }) {
  return (
    <div style={{ padding: "10px 14px", background: "var(--surface-sunken)", borderRadius: 10 }}>
      <div style={{ fontSize: 18, fontWeight: 700 }}>{value}</div>
      <div style={{ fontSize: 10, color: "var(--text-tertiary)", marginTop: 2, textTransform: "uppercase" }}>{label}</div>
    </div>
  );
}

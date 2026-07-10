"use client";
import { useCallback } from "react";
import { adminInvoiceApi, type ServiceInvoiceRecord } from "../../../lib/api";
import { Card, Badge, Btn, Skeleton } from "../../../components/shared/ui";
import { useApi } from "../../../hooks/useApi";
import { FileText, RefreshCw } from "lucide-react";

function statusVariant(s: string): "success" | "warning" | "danger" | "info" | "default" {
  if (s === "paid") return "success";
  if (s === "payment_collected" || s === "issued") return "info";
  if (s === "payment_pending") return "warning";
  if (s === "cancelled" || s === "failed") return "danger";
  return "default";
}

export default function AdminServiceInvoicesPage() {
  const { data, loading, refetch } = useApi(
    useCallback(() => adminInvoiceApi.list(), [])
  );

  const invoices: ServiceInvoiceRecord[] = (Array.isArray(data) ? data : []) as ServiceInvoiceRecord[];

  return (
    <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 24, maxWidth: 1100 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: 0,
            display: "flex", alignItems: "center", gap: 10 }}>
            <FileText size={22} /> Service Invoices
          </h1>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "6px 0 0" }}>
            All invoices across all providers.
          </p>
        </div>
        <Btn variant="ghost" onClick={refetch}><RefreshCw size={14} /> Refresh</Btn>
      </div>

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {[0,1,2,3].map(i => <Skeleton key={i} height={64} />)}
        </div>
      ) : invoices.length === 0 ? (
        <Card padding={48} style={{ textAlign: "center" }}>
          <FileText size={32} style={{ color: "var(--text-tertiary)", margin: "0 auto 12px" }} />
          <p style={{ color: "var(--text-secondary)", margin: 0 }}>No invoices found.</p>
        </Card>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {invoices.map((inv: ServiceInvoiceRecord) => (
            <Card key={inv.id} padding={14}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
                <div>
                  <p style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary)", margin: 0 }}>
                    #{inv.invoice_number ?? inv.id.slice(0, 8)} · {inv.source?.replace(/_/g, " ")}
                  </p>
                  <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "2px 0 0" }}>
                    Tenant: {inv.tenant_id?.slice(0, 8)} · Job: {inv.job_id?.slice(0, 8)}
                  </p>
                </div>
                <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                  <span style={{ fontSize: 13, fontWeight: 600 }}>{inv.customer_payable_amount ?? "—"}</span>
                  <Badge variant={statusVariant(inv.invoice_status)}>{inv.invoice_status?.replace(/_/g, " ")}</Badge>
                  {inv.payment_status && (
                    <Badge variant={statusVariant(inv.payment_status)}>{inv.payment_status.replace(/_/g, " ")}</Badge>
                  )}
                  <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                    {inv.created_at ? new Date(inv.created_at).toLocaleDateString() : "—"}
                  </span>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

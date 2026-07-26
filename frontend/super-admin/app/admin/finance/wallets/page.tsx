"use client";
import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { Wallet, RefreshCw, Search } from "lucide-react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, DataTable, SectionHeader } from "../../../../components/shared/ui";
import { financeApi } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";
import type { FinanceWallet } from "../../../../lib/api";

const HEALTH_BADGE: Record<string, "success" | "info" | "warning" | "danger" | "muted"> = {
  platinum: "success", gold: "success", silver: "info", bronze: "warning", at_risk: "warning", critical: "danger",
};

export default function WalletDirectoryPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const wallets = useApi(useCallback(() => financeApi.listWallets({ q: search || undefined, pageSize: 200 }), [search]));
  const rows = wallets.data?.items ?? [];

  const columns = [
    { key: "tenant_name", label: "Tenant", render: (_: unknown, row: FinanceWallet) => row.tenant_name },
    { key: "available_balance", label: "Available Balance", width: 150, render: (_: unknown, row: FinanceWallet) => `₹${row.available_balance.toLocaleString("en-IN")}` },
    { key: "reserved_balance", label: "Reserved Balance", width: 150, render: (_: unknown, row: FinanceWallet) => `₹${row.reserved_balance.toLocaleString("en-IN")}` },
    { key: "low_balance_threshold", label: "Low-Balance Threshold", width: 170, render: (_: unknown, row: FinanceWallet) => row.low_balance_threshold != null ? `₹${row.low_balance_threshold.toLocaleString("en-IN")}` : "—" },
    { key: "last_transaction_at", label: "Last Transaction", width: 150, render: (_: unknown, row: FinanceWallet) => row.last_transaction_at ? new Date(row.last_transaction_at).toLocaleDateString("en-IN") : "—" },
    { key: "health_band", label: "Health Band", width: 130, render: (_: unknown, row: FinanceWallet) => <Badge variant={HEALTH_BADGE[row.health_band] ?? "muted"}>{row.health_band}</Badge> },
    { key: "is_active", label: "Status", width: 100, render: (_: unknown, row: FinanceWallet) => <Badge variant={row.is_active ? "success" : "muted"}>{row.is_active ? "Active" : "Inactive"}</Badge> },
  ];

  return (
    <AdminLayout activeNav="finance">
      <SectionHeader title="Tenant Balance Directory" subtitle="Tenant platform credit balances (billing engine), ordered by lowest balance first. Note: this is a separate ledger from the authoritative Usage Credits system at /admin/finance/usage-credits — see E2E-05 report for the architecture split."/>
      <div style={{ padding: "0 28px 32px" }}>
        <Card padding={16}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <Wallet size={18} color="var(--brand)"/>
              <span style={{ fontWeight: 700, fontSize: 15 }}>Tenant Balances</span>
              <Badge variant="muted">{rows.length}</Badge>
            </div>
            <Btn variant="secondary" size="sm" icon={<RefreshCw size={13}/>} onClick={() => wallets.refetch()}>Refresh</Btn>
          </div>
          <div style={{ position: "relative", marginBottom: 12 }}>
            <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)" }}/>
            <input placeholder="Search tenant…" value={search} onChange={e => setSearch(e.target.value)}
              style={{ width: "100%", height: 34, paddingLeft: 32, paddingRight: 12, fontSize: 13, borderRadius:"var(--radius-md)",
                border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)",
                outline: "none", fontFamily: "inherit", boxSizing: "border-box" }}/>
          </div>
          <DataTable columns={columns as unknown as Parameters<typeof DataTable>[0]["columns"]}
            rows={rows as unknown as Record<string, unknown>[]} loading={wallets.loading}
            emptyText="No wallets found."
            onRowClick={(row) => router.push(`/admin/finance/wallets/${(row as unknown as FinanceWallet).wallet_id}`)}/>
        </Card>
      </div>
    </AdminLayout>
  );
}

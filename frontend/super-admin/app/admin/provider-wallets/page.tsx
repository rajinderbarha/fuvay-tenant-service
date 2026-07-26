"use client";
import { useCallback, useState } from "react";
import { adminWalletApi, type WalletRecord } from "../../../lib/api";
import { Card, Badge, Btn, Skeleton, Toaster, type ToastItem } from "../../../components/shared/ui";
import { useApi, useAction } from "../../../hooks/useApi";
import { Wallet, RefreshCw, PlusCircle } from "lucide-react";

export default function AdminProviderWalletsPage() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const addToast = useCallback((title: string, variant: ToastItem["variant"] = "success") => {
    const id = Math.random().toString(36).slice(2);
    setToasts(prev => [...prev, { id, title, variant }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 3500);
  }, []);

  const [creditTarget, setCreditTarget] = useState<string | null>(null);
  const [creditAmount, setCreditAmount] = useState("");
  const [creditReason, setCreditReason] = useState("");

  const { data, loading, refetch } = useApi(
    useCallback(() => adminWalletApi.list(), [])
  );

  const wallets: WalletRecord[] = (Array.isArray(data) ? data : []) as WalletRecord[];

  const creditAction = useAction(
    useCallback(
      (tenantId: string, amount: number, reason: string) =>
        adminWalletApi.credit(tenantId, { amount, reason }),
      []
    )
  );

  const handleCredit = async () => {
    if (!creditTarget) return;
    const result = await creditAction.execute(creditTarget, Number(creditAmount), creditReason || "Admin credit");
    if (result) {
      addToast("Wallet credited.", "success");
      setCreditTarget(null); setCreditAmount(""); setCreditReason("");
      refetch();
    } else {
      addToast(creditAction.error ?? "Credit failed.", "danger");
    }
  };

  return (
    <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 24, maxWidth: 1100 }}>
      <Toaster toasts={toasts} onRemove={id => setToasts(p => p.filter(t => t.id !== id))} />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: 0,
            display: "flex", alignItems: "center", gap: 10 }}>
            <Wallet size={22} /> Provider Wallets
          </h1>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "6px 0 0" }}>
            Credit balances for all provider tenants.
          </p>
        </div>
        <Btn variant="ghost" onClick={refetch}><RefreshCw size={14} /> Refresh</Btn>
      </div>

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {[0,1,2].map(i => <Skeleton key={i} height={80} />)}
        </div>
      ) : wallets.length === 0 ? (
        <Card padding={48} style={{ textAlign: "center" }}>
          <Wallet size={32} style={{ color: "var(--text-tertiary)", margin: "0 auto 12px" }} />
          <p style={{ color: "var(--text-secondary)", margin: 0 }}>No provider wallets found.</p>
        </Card>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {wallets.map((w: WalletRecord) => (
            <Card key={w.tenant_id} padding={16}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 8 }}>
                <div>
                  <p style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary)", margin: 0 }}>
                    Tenant: {w.tenant_id?.slice(0, 12)}
                  </p>
                  <div style={{ display: "flex", gap: 16, marginTop: 6, fontSize: 12, flexWrap: "wrap" }}>
                    <span><strong>Balance:</strong> {w.current_balance}</span>
                    <span><strong>Reserved:</strong> {w.reserved_balance}</span>
                    <span><strong>In:</strong> {w.total_purchased}</span>
                    <span><strong>Out:</strong> {w.total_deducted}</span>
                  </div>
                </div>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <Badge variant={w.is_active ? "success" : "danger"}>{w.is_active ? "Active" : "Inactive"}</Badge>
                  <Btn size="sm" onClick={() => setCreditTarget(w.tenant_id)}>
                    <PlusCircle size={12} /> Add Credit
                  </Btn>
                </div>
              </div>

              {creditTarget === w.tenant_id && (
                <div style={{ marginTop: 12, padding: "12px", background: "var(--surface-sunken)",
                  borderRadius:"var(--radius-md)", display: "flex", flexDirection: "column", gap: 8 }}>
                  <input
                    type="number"
                    placeholder="Amount"
                    value={creditAmount}
                    onChange={e => setCreditAmount(e.target.value)}
                    style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border)",
                      background: "var(--surface)", fontSize: 13 }}
                  />
                  <input
                    type="text"
                    placeholder="Reason (optional)"
                    value={creditReason}
                    onChange={e => setCreditReason(e.target.value)}
                    style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border)",
                      background: "var(--surface)", fontSize: 13 }}
                  />
                  <div style={{ display: "flex", gap: 8 }}>
                    <Btn size="sm" onClick={handleCredit} loading={creditAction.loading}>
                      Confirm Credit
                    </Btn>
                    <Btn size="sm" variant="ghost" onClick={() => setCreditTarget(null)}>Cancel</Btn>
                  </div>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

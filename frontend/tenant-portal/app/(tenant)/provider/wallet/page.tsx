"use client";
import { useCallback, useState } from "react";
import { providerWalletApi, type WalletRecord, type WalletTransactionRecord } from "../../../../lib/api";
import { Card, Badge, Btn, Skeleton, Toaster, type ToastItem } from "../../../../components/shared/ui";
import { useApi } from "../../../../hooks/useApi";
import { Wallet, RefreshCw, TrendingDown, TrendingUp } from "lucide-react";

type ActiveTab = "summary" | "ledger" | "commissions";

export default function ProviderWalletPage() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const addToast = useCallback((title: string, variant: ToastItem["variant"] = "success") => {
    const id = Math.random().toString(36).slice(2);
    setToasts(prev => [...prev, { id, title, variant }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 3500);
  }, []);

  const [tab, setTab] = useState<ActiveTab>("summary");

  const { data: walletData, loading: walletLoading, refetch: refetchWallet } = useApi(
    useCallback(() => providerWalletApi.getWallet(), [])
  );
  const { data: ledgerData, loading: ledgerLoading, refetch: refetchLedger } = useApi(
    useCallback(() => providerWalletApi.getLedger(), [])
  );
  const { data: commissionsData, loading: commissionsLoading, refetch: refetchCommissions } = useApi(
    useCallback(() => providerWalletApi.getCommissions(), [])
  );

  const wallet: WalletRecord | undefined = walletData ?? undefined;
  const ledger: WalletTransactionRecord[] = (Array.isArray(ledgerData) ? ledgerData : []) as WalletTransactionRecord[];
  const commissions: Record<string, unknown>[] = (Array.isArray(commissionsData) ? commissionsData : []) as Record<string, unknown>[];

  const refetchAll = () => { refetchWallet(); refetchLedger(); refetchCommissions(); };

  const tabStyle = (t: ActiveTab) => ({
    padding: "8px 16px",
    borderRadius: 6,
    border: "none",
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 500,
    background: tab === t ? "var(--brand)" : "var(--surface-sunken)",
    color: tab === t ? "#fff" : "var(--text-secondary)",
  } as React.CSSProperties);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24, maxWidth: 900 }}>
      <Toaster toasts={toasts} onRemove={id => setToasts(p => p.filter(t => t.id !== id))} />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: 0,
            display: "flex", alignItems: "center", gap: 10 }}>
            <Wallet size={22} /> Credit Wallet
          </h1>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "6px 0 0" }}>
            Your platform credit balance and commission history.
          </p>
        </div>
        <Btn variant="ghost" onClick={refetchAll}><RefreshCw size={14} /> Refresh</Btn>
      </div>

      {/* Wallet summary card */}
      {walletLoading ? (
        <Skeleton height={100} />
      ) : wallet ? (
        <Card padding={20}>
          <div style={{ display: "flex", gap: 32, flexWrap: "wrap" }}>
            <div>
              <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>Usage Credit Balance</p>
              <p style={{ fontSize: 28, fontWeight: 700, color: "var(--text-primary)", margin: "4px 0 0" }}>
                {wallet.current_balance}
              </p>
            </div>
            <div>
              <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>Reserved</p>
              <p style={{ fontSize: 20, fontWeight: 600, color: "var(--text-secondary)", margin: "4px 0 0" }}>
                {wallet.reserved_balance}
              </p>
            </div>
            <div>
              <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>Total Purchased</p>
              <p style={{ fontSize: 20, fontWeight: 600, color: "var(--text-secondary)", margin: "4px 0 0" }}>
                {wallet.total_purchased}
              </p>
            </div>
            <div>
              <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>Total Commission Deducted</p>
              <p style={{ fontSize: 20, fontWeight: 600, color: "var(--text-secondary)", margin: "4px 0 0" }}>
                {wallet.total_deducted}
              </p>
            </div>
          </div>
          {wallet.is_active === false && (
            <p style={{ fontSize: 12, color: "var(--danger-text)", margin: "12px 0 0" }}>Wallet is inactive. Contact support.</p>
          )}
        </Card>
      ) : (
        <Card padding={20}><p style={{ color: "var(--text-tertiary)", margin: 0 }}>No wallet found. Contact admin to provision.</p></Card>
      )}

      {/* Tabs */}
      <div style={{ display: "flex", gap: 8 }}>
        <button style={tabStyle("summary")} onClick={() => setTab("summary")}>Summary</button>
        <button style={tabStyle("ledger")} onClick={() => setTab("ledger")}>Ledger</button>
        <button style={tabStyle("commissions")} onClick={() => setTab("commissions")}>Commissions</button>
      </div>

      {tab === "ledger" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {ledgerLoading ? (
            [0,1,2].map(i => <Skeleton key={i} height={56} />)
          ) : ledger.length === 0 ? (
            <Card padding={32} style={{ textAlign: "center" }}>
              <p style={{ color: "var(--text-tertiary)", margin: 0 }}>No transactions yet.</p>
            </Card>
          ) : ledger.map((t: WalletTransactionRecord) => (
            <Card key={t.id} padding={12}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  {t.txn_type?.includes("debit") || t.txn_type?.includes("commission")
                    ? <TrendingDown size={14} style={{ color: "var(--danger)" }} />
                    : <TrendingUp size={14} style={{ color: "var(--success)" }} />}
                  <div>
                    <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)", margin: 0 }}>
                      {t.txn_type?.replace(/_/g, " ")}
                    </p>
                    <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "2px 0 0" }}>
                      {t.description ?? "—"} · {t.created_at ? new Date(t.created_at).toLocaleDateString() : "—"}
                    </p>
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <p style={{ fontWeight: 600, fontSize: 14, color: "var(--text-primary)", margin: 0 }}>{t.amount}</p>
                  <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "2px 0 0" }}>
                    Balance: {t.balance_after}
                  </p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {tab === "commissions" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {commissionsLoading ? (
            [0,1,2].map(i => <Skeleton key={i} height={56} />)
          ) : commissions.length === 0 ? (
            <Card padding={32} style={{ textAlign: "center" }}>
              <p style={{ color: "var(--text-tertiary)", margin: 0 }}>No commission records yet.</p>
            </Card>
          ) : commissions.map((c: Record<string, unknown>) => (
            <Card key={c.id as string} padding={12}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)", margin: 0 }}>
                    Invoice: {(c.invoice_id as string)?.slice(0, 8)}
                  </p>
                  <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "2px 0 0" }}>
                    Rate: {c.commission_rate as string}% · {(c.created_at as string) ? new Date(c.created_at as string).toLocaleDateString() : "—"}
                  </p>
                </div>
                <div style={{ textAlign: "right" }}>
                  <Badge variant={c.status === "deducted" ? "success" : c.status === "insufficient_credit" ? "danger" : "warning"}>
                    {(c.status as string)?.replace(/_/g, " ")}
                  </Badge>
                  <p style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary)", margin: "4px 0 0" }}>
                    {c.commission_amount as string}
                  </p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {tab === "summary" && (
        <Card padding={20}>
          <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: 0 }}>
            Your credit wallet is used for platform commission deductions. Each completed job deducts
            a commission from your balance. Ensure your wallet has sufficient credit to avoid service interruptions.
          </p>
        </Card>
      )}
    </div>
  );
}

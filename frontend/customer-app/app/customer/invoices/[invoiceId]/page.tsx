"use client";
/**
 * MODULE-L5-18 — Customer invoice detail + receipt.
 *
 * Shows the invoice breakdown and, for pay-provider-directly home services, lets
 * the customer confirm it paid the provider on-site (customer_confirm_payment).
 */
import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import ErrorBanner from "../../../../components/ErrorBanner";
import { getInvoice, confirmPayment, applyCreditToInvoice, Invoice } from "../../../../lib/api/customer-invoices";
import { getCreditSummary } from "../../../../lib/api/customer-credits";

const money = (v?: string | null, ccy?: string | null) =>
  v == null ? "—" : `${ccy ?? "₹"}${Number(v).toLocaleString()}`;

export default function CustomerInvoiceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const invoiceId = params.invoiceId as string;

  const [inv, setInv] = useState<Invoice | null>(null);
  const [creditBalance, setCreditBalance] = useState(0);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [ok, setOk] = useState<string | null>(null);

  const load = useCallback(() => {
    getInvoice(invoiceId).then(setInv).catch(setError);
    getCreditSummary().then((s) => setCreditBalance(s.active_credit_balance)).catch(() => {});
  }, [invoiceId]);
  useEffect(() => { load(); }, [load]);

  async function doConfirm() {
    setBusy(true); setError(null); setOk(null);
    try {
      await confirmPayment(invoiceId);
      setOk("Thanks — we've recorded that you paid the provider.");
      load();
    } catch (e) { setError(e); } finally { setBusy(false); }
  }

  async function doApplyCredit() {
    if (!inv) return;
    const payable = Number(inv.customer_payable_amount);
    const use = Math.min(creditBalance, payable);
    setBusy(true); setError(null); setOk(null);
    try {
      const res = await applyCreditToInvoice(invoiceId, use);
      setOk(`Applied ${ccy}${res.credit_applied.toLocaleString()} credit. You now pay ${ccy}${res.new_payable.toLocaleString()}.`);
      load();
    } catch (e) { setError(e); } finally { setBusy(false); }
  }

  const paid = inv && ["paid", "payment_collected"].includes(inv.status);
  const ccy = inv?.currency ?? "₹";
  const creditApplied = inv ? Number(inv.credit_applied_amount ?? 0) : 0;
  const canApplyCredit = !!inv && !paid && creditApplied === 0 && creditBalance > 0
    && Number(inv.customer_payable_amount) > 0;

  return (
    <div className="co-container">
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 0" }}>
        <button onClick={() => router.push("/customer/invoices")}
          style={{ background: "none", border: "none", fontSize: 22, cursor: "pointer" }}>‹</button>
        <h1 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Invoice</h1>
      </div>
      <ErrorBanner error={error} />
      {ok && <div className="co-card" style={{ background: "#ecfdf3", color: "#0a7c3f", marginBottom: 12 }}>{ok}</div>}

      {inv === null ? (
        <div className="co-card">Loading…</div>
      ) : (
        <>
          <div className="co-card" style={{ marginBottom: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontWeight: 700 }}>#{inv.invoice_number}</div>
              <span style={{ fontSize: 12, fontWeight: 600 }}>{inv.payment_mode}</span>
            </div>

            <div style={{ margin: "12px 0", display: "flex", flexDirection: "column", gap: 4 }}>
              {(inv.items ?? []).map((it) => (
                <div key={it.id} style={{ display: "flex", justifyContent: "space-between", fontSize: 14 }}>
                  <span>{it.description ?? "Item"}{it.quantity ? ` ×${it.quantity}` : ""}</span>
                  <span>{money(String(it.line_total ?? it.unit_price ?? ""), ccy)}</span>
                </div>
              ))}
              <Row label="Subtotal" value={money(inv.subtotal_amount, ccy)} />
              {Number(inv.discount_amount) > 0 && <Row label="Discount" value={`-${money(inv.discount_amount, ccy)}`} />}
              {Number(inv.tax_amount) > 0 && <Row label="Tax" value={money(inv.tax_amount, ccy)} />}
              {creditApplied > 0 && (
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 14, color: "#0a7c3f" }}>
                  <span>Service credit applied</span><span>-{money(inv.credit_applied_amount, ccy)}</span>
                </div>
              )}
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 800, fontSize: 18,
              borderTop: "1px solid var(--border)", paddingTop: 10 }}>
              <span>You pay</span><span>{money(inv.customer_payable_amount, ccy)}</span>
            </div>
          </div>

          {canApplyCredit && (
            <div className="co-card" style={{ marginBottom: 12, display: "flex",
              justifyContent: "space-between", alignItems: "center", background: "#f0fdf4" }}>
              <div>
                <div style={{ fontWeight: 600 }}>Use your credit</div>
                <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                  You have {ccy}{creditBalance.toLocaleString()} available
                </div>
              </div>
              <button className="co-btn-secondary" disabled={busy} onClick={doApplyCredit}>
                {busy ? "…" : "Apply credit"}
              </button>
            </div>
          )}

          {paid ? (
            <div className="co-card" style={{ textAlign: "center", color: "#0a7c3f", fontWeight: 600 }}>
              ✓ Paid{inv.paid_at ? ` on ${new Date(inv.paid_at).toLocaleDateString()}` : ""}
            </div>
          ) : (
            <button className="co-btn-primary" style={{ width: "100%" }} disabled={busy}
              onClick={doConfirm}>{busy ? "…" : "I've paid the provider"}</button>
          )}
        </>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 14, color: "var(--text-secondary)" }}>
      <span>{label}</span><span>{value}</span>
    </div>
  );
}

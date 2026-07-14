"use client";
/**
 * MODULE-L5-10 — Category Rates: provider commission + customer charge.
 *
 * The platform earns from BOTH sides of a job, set per category:
 *   - Commission %  — the platform's cut of the invoice, deducted from the provider.
 *   - Customer Charge % — a platform fee added to what the customer pays, shown
 *     to the customer as included. e.g. a Rs.500 service at 10% is shown as
 *     Rs.550 ("Rs.50 platform fee included").
 * Commission was previously a hardcoded flat 10%; the customer charge did not
 * exist at all.
 */
import React, { useCallback, useState } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, SectionHeader, Btn, Badge, Spinner, Input } from "../../../../components/shared/ui";
import { catalogApi, CategoryCommissionRate } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { RequirePermission } from "../../../../components/shared/PermissionGate";

export default function CategoryRatesPage() {
  const rates = useApi(useCallback(() => catalogApi.listCategoryCommissionRates(), []), []);
  const [comm, setComm] = useState<Record<string, string>>({});
  const [charge, setCharge] = useState<Record<string, string>>({});
  const [savingId, setSavingId] = useState<string | null>(null);

  const saveComm = useAction(async (id: string, pct: number | null) => {
    setSavingId(id);
    try { const r = await catalogApi.setCategoryCommissionRate(id, pct); rates.refetch(); return r; }
    finally { setSavingId(null); }
  });
  const saveCharge = useAction(async (id: string, pct: number | null) => {
    setSavingId(id);
    try { const r = await catalogApi.setCategoryCustomerCharge(id, pct); rates.refetch(); return r; }
    finally { setSavingId(null); }
  });

  const rows: CategoryCommissionRate[] = rates.data ?? [];
  const defaultPct = rows[0]?.default_pct ?? 10;

  const parse = (s: string): number | null => {
    if (s.trim() === "") return null;
    const n = Number(s);
    return Number.isNaN(n) || n < 0 || n > 100 ? undefined as unknown as null : n;
  };

  return (
    <AdminLayout activeNav="catalog">
      <RequirePermission requiredPermission="platform:pricing:read" parentLabel="Pricing">
        <SectionHeader
          title="Category Rates"
          subtitle={`The platform earns from both sides of a job, per category: a commission from the provider (default ${defaultPct}%) and a customer charge added to what the customer pays (shown to them as included).`}
        />

        {rates.loading ? <Spinner /> : rates.error ? (
          <Card><p style={{ color: "var(--danger)" }}>{rates.error}</p></Card>
        ) : (
          <Card padding={0}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
                <thead>
                  <tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
                    <th style={{ padding: "12px 16px" }}>Category</th>
                    <th style={{ padding: "12px 16px" }}>Provider Commission %</th>
                    <th style={{ padding: "12px 16px" }}>Customer Charge %</th>
                    <th style={{ padding: "12px 16px" }}>Example on ₹500</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map(c => {
                    const commVal = comm[c.id] ?? (c.commission_pct != null ? String(c.commission_pct) : "");
                    const chargeVal = charge[c.id] ?? (c.customer_charge_pct != null ? String(c.customer_charge_pct) : "");
                    const commDirty = (comm[c.id] ?? "") !== "" && Number(comm[c.id]) !== (c.commission_pct ?? NaN);
                    const chargeDirty = (charge[c.id] ?? "") !== "" && Number(charge[c.id]) !== (c.customer_charge_pct ?? NaN);
                    const chargePct = c.customer_charge_pct ?? 0;
                    const commPct = c.effective_pct;
                    const custPays = Math.round(500 * (1 + chargePct / 100));
                    const platGets = Math.round(500 * chargePct / 100) + Math.round(500 * commPct / 100);
                    return (
                      <tr key={c.id} style={{ borderBottom: "1px solid var(--border)" }}>
                        <td style={{ padding: "10px 16px", fontWeight: 600 }}>
                          {c.name}
                          {!c.is_active && <Badge variant="muted" size="sm">inactive</Badge>}
                        </td>

                        <td style={{ padding: "10px 16px" }}>
                          <div style={{ display: "flex", gap: 8, alignItems: "center", maxWidth: 220 }}>
                            <Input type="number" value={commVal}
                              placeholder={`default (${c.default_pct}%)`}
                              onChange={(v: string) => setComm(d => ({ ...d, [c.id]: v }))} />
                            <Btn size="sm" disabled={!commDirty || savingId === c.id}
                              onClick={() => { const n = parse(comm[c.id]); if (n === undefined) return; saveComm.execute(c.id, n); }}>
                              Save
                            </Btn>
                            {!c.using_default && (
                              <Btn size="sm" variant="ghost" disabled={savingId === c.id}
                                onClick={() => { setComm(d => ({ ...d, [c.id]: "" })); saveComm.execute(c.id, null); }}>
                                Reset
                              </Btn>
                            )}
                          </div>
                        </td>

                        <td style={{ padding: "10px 16px" }}>
                          <div style={{ display: "flex", gap: 8, alignItems: "center", maxWidth: 220 }}>
                            <Input type="number" value={chargeVal} placeholder="0%"
                              onChange={(v: string) => setCharge(d => ({ ...d, [c.id]: v }))} />
                            <Btn size="sm" disabled={!chargeDirty || savingId === c.id}
                              onClick={() => { const n = parse(charge[c.id]); if (n === undefined) return; saveCharge.execute(c.id, n); }}>
                              Save
                            </Btn>
                            {c.customer_charge_pct != null && (
                              <Btn size="sm" variant="ghost" disabled={savingId === c.id}
                                onClick={() => { setCharge(d => ({ ...d, [c.id]: "" })); saveCharge.execute(c.id, null); }}>
                                Clear
                              </Btn>
                            )}
                          </div>
                        </td>

                        <td style={{ padding: "10px 16px", fontSize: 13, color: "var(--text-secondary)" }}>
                          Customer pays <strong>₹{custPays}</strong>
                          {chargePct ? <span style={{ color: "var(--text-tertiary)" }}> (incl. ₹{Math.round(500 * chargePct / 100)} fee)</span> : null}
                          <br />Platform earns <strong>₹{platGets}</strong>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        )}

        {(saveComm.error || saveCharge.error) &&
          <p style={{ color: "var(--danger)", fontSize: 13, marginTop: 10 }}>{saveComm.error || saveCharge.error}</p>}
      </RequirePermission>
    </AdminLayout>
  );
}

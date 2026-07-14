"use client";
/**
 * MODULE-L5-10 — Category Commission Rates.
 *
 * Commission on every service invoice used to be a hardcoded flat 10% for every
 * category, regardless of value — the same cut on a Rs.200 salon visit and a
 * Rs.50,000 real-estate deal. This page lets the admin set the commission rate
 * per category; a category left blank uses the platform default (10%).
 */
import React, { useCallback, useState } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, SectionHeader, Btn, Badge, Spinner, Input } from "../../../../components/shared/ui";
import { catalogApi, CategoryCommissionRate } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { RequirePermission } from "../../../../components/shared/PermissionGate";

export default function CategoryCommissionPage() {
  const rates = useApi(useCallback(() => catalogApi.listCategoryCommissionRates(), []), []);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [savingId, setSavingId] = useState<string | null>(null);

  // admin useAction takes only the action (no options) — refetch inside.
  const save = useAction(async (id: string, pct: number | null) => {
    setSavingId(id);
    try {
      const res = await catalogApi.setCategoryCommissionRate(id, pct);
      rates.refetch();
      return res;
    } finally { setSavingId(null); }
  });

  const rows: CategoryCommissionRate[] = rates.data ?? [];
  const defaultPct = rows[0]?.default_pct ?? 10;

  return (
    <AdminLayout activeNav="catalog">
      <RequirePermission requiredPermission="platform:pricing:read" parentLabel="Pricing">
        <SectionHeader
          title="Category Commission Rates"
          subtitle={`The platform's cut of each completed job's invoice, set per category. A category left on “default” uses ${defaultPct}%.`}
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
                    <th style={{ padding: "12px 16px" }}>Vertical</th>
                    <th style={{ padding: "12px 16px" }}>Commission %</th>
                    <th style={{ padding: "12px 16px" }}>Applies</th>
                    <th style={{ padding: "12px 16px", width: 220 }}></th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map(c => {
                    const val = draft[c.id] ?? (c.commission_pct != null ? String(c.commission_pct) : "");
                    const dirty = (draft[c.id] ?? "") !== "" &&
                                  Number(draft[c.id]) !== (c.commission_pct ?? NaN);
                    return (
                      <tr key={c.id} style={{ borderBottom: "1px solid var(--border)" }}>
                        <td style={{ padding: "10px 16px", fontWeight: 600 }}>
                          {c.name}
                          {!c.is_active && <Badge variant="muted" size="sm">inactive</Badge>}
                        </td>
                        <td style={{ padding: "10px 16px", color: "var(--text-tertiary)" }}>
                          {c.vertical_type ?? "—"}
                        </td>
                        <td style={{ padding: "10px 16px", maxWidth: 140 }}>
                          <Input
                            type="number"
                            value={val}
                            placeholder={`default (${c.default_pct}%)`}
                            onChange={(v: string) => setDraft(d => ({ ...d, [c.id]: v }))}
                          />
                        </td>
                        <td style={{ padding: "10px 16px" }}>
                          {c.using_default
                            ? <Badge variant="muted">default {c.default_pct}%</Badge>
                            : <Badge variant="info">{c.effective_pct}%</Badge>}
                        </td>
                        <td style={{ padding: "10px 16px" }}>
                          <div style={{ display: "flex", gap: 8 }}>
                            <Btn size="sm" disabled={!dirty || savingId === c.id}
                              onClick={() => {
                                const n = Number(draft[c.id]);
                                if (Number.isNaN(n) || n < 0 || n > 100) return;
                                save.execute(c.id, n);
                              }}>
                              {savingId === c.id ? "Saving…" : "Save"}
                            </Btn>
                            {!c.using_default && (
                              <Btn size="sm" variant="ghost" disabled={savingId === c.id}
                                onClick={() => { setDraft(d => ({ ...d, [c.id]: "" })); save.execute(c.id, null); }}>
                                Reset to default
                              </Btn>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        )}

        {save.error && <p style={{ color: "var(--danger)", fontSize: 13, marginTop: 10 }}>{save.error}</p>}
      </RequirePermission>
    </AdminLayout>
  );
}

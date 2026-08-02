"use client";
/**
 * Customers — filterable by health band, searchable, paginated.
 * PROVEN: customersApi.list() connected with health_band + cursor params.
 */
import React, { useCallback, useState } from "react";
import { TenantLayout }                 from "../../../components/layout/TenantLayout";
import { Card, Skeleton, PageHeader, Input, Button, EmptyState } from "@serviceos/design-system";
import { HealthMeter, Badge }            from "../../../components/shared/ui";
import { customersApi }                 from "../../../lib/api";
import { useApi }                       from "../../../hooks/useApi";

const HEALTH_TABS = [
  { key:"",         label:"All Customers", color:"" },
  { key:"platinum", label:"Platinum",      color:"var(--warning-text)"  },
  { key:"gold",     label:"Gold",          color:"var(--warning-text)"  },
  { key:"silver",   label:"Silver",        color:"var(--text-tertiary)" },
  { key:"bronze",   label:"Bronze",        color:"var(--text-secondary)"},
  { key:"at_risk",  label:"At Risk",       color:"var(--warning-text)"  },
  { key:"critical", label:"Critical",      color:"var(--danger-text)"   },
] as const;

export default function CustomersPage() {
  const [search,    setSearch]    = useState("");
  const [bandTab,   setBandTab]   = useState("");
  const [cursor,    setCursor]    = useState<string | undefined>(undefined);
  const [prevStack, setPrevStack] = useState<string[]>([]);

  const params = useCallback(() =>
    customersApi.list({
      limit:"30",
      ...(bandTab ? { health_band: bandTab } : {}),
      ...(cursor  ? { cursor }               : {}),
    }), [bandTab, cursor]);
  const customers = useApi(params);

  const filtered = (customers.data?.customers ?? []).filter(c => {
    if (!search) return true;
    const q = search.toLowerCase();
    return c.name.toLowerCase().includes(q) || (c.phone?.includes(q) ?? false);
  });

  function handleNext() {
    const nc = customers.data?.next_cursor;
    if (!nc) return;
    setPrevStack(ps => [...ps, cursor ?? ""]);
    setCursor(nc);
  }
  function handlePrev() {
    const prev = [...prevStack];
    const c    = prev.pop();
    setPrevStack(prev);
    setCursor(c || undefined);
  }
  function handleTabChange(key: string) {
    setBandTab(key); setCursor(undefined); setPrevStack([]);
  }

  const fmt = (n: number) => `₹${n.toLocaleString("en-IN")}`;

  return (
    <TenantLayout activeNav="customers">
      <PageHeader
        title="Customers"
        description={customers.loading ? "Loading…" : `${customers.data?.total ?? 0} customers`}
      />

      {/* Health band tabs */}
      <div style={{ display:"flex", gap:4, marginBottom:14, marginTop:16, flexWrap:"wrap",
        padding:"4px", background:"var(--surface-sunken)",
        borderRadius:10, border:"1px solid var(--border)", width:"fit-content" }}>
        {HEALTH_TABS.map(t => (
          <button key={t.key} onClick={() => handleTabChange(t.key)}
            style={{ padding:"6px 14px", borderRadius:"var(--radius-md)", border:"none", cursor:"pointer",
              fontFamily:"inherit", fontSize:12, fontWeight: bandTab===t.key ? 700 : 500,
              background: bandTab===t.key ? "var(--surface-base)" : "transparent",
              color: bandTab===t.key ? (t.color || "var(--brand)") : "var(--text-secondary)",
              boxShadow: bandTab===t.key ? "var(--shadow-xs)" : "none",
              transition:"all 0.12s" }}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Search */}
      <div style={{ marginBottom:14, maxWidth:400 }}>
        <Input value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Search by name or phone…"
        />
      </div>

      {/* Table */}
      {customers.loading ? (
        <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
          {[...Array(6)].map((_,i) => <Skeleton key={i} height="3.5rem" radius="8px" />)}
        </div>
      ) : filtered.length === 0 ? (
        <Card style={{ textAlign:"center" }}>
          <EmptyState
            title={search ? `No customers matching "${search}"` : "No customers in this health band"}
          />
        </Card>
      ) : (
        <>
          <Card padding="none" style={{ overflow:"hidden" }}>
            <div style={{ overflowX:"auto" }}>
              <table style={{ width:"100%", borderCollapse:"collapse" }}>
                <thead>
                  <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
                    {["Customer","Phone","Health","Total Jobs","Spend","LTV","Last Job"].map(h => (
                      <th key={h} style={{ padding:"10px 16px", textAlign:"left", fontSize:11,
                        fontWeight:700, color:"var(--text-tertiary)", letterSpacing:"0.06em",
                        textTransform:"uppercase", whiteSpace:"nowrap" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((c, i) => (
                    <tr key={c.id}
                      onClick={() => window.location.href = `/customers/${c.id}`}
                      style={{ borderBottom: i < filtered.length-1 ? "1px solid var(--border)" : "none",
                        cursor:"pointer", transition:"background 0.1s" }}
                      onMouseEnter={e => (e.currentTarget as HTMLTableRowElement).style.background="var(--surface-sunken)"}
                      onMouseLeave={e => (e.currentTarget as HTMLTableRowElement).style.background="transparent"}>
                      <td style={{ padding:"12px 16px" }}>
                        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                          <div style={{ width:32, height:32, borderRadius:"50%",
                            background:"var(--accent-muted)", display:"flex",
                            alignItems:"center", justifyContent:"center",
                            fontSize:13, fontWeight:700, color:"var(--accent)", flexShrink:0 }}>
                            {c.name[0].toUpperCase()}
                          </div>
                          <span style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)" }}>
                            {c.name}
                          </span>
                        </div>
                      </td>
                      <td style={{ padding:"12px 16px", fontSize:12, color:"var(--text-secondary)" }}>
                        {c.phone ?? "—"}
                      </td>
                      <td style={{ padding:"12px 16px", width:150 }}>
                        <div style={{ width:130 }}>
                          <HealthMeter score={c.health_score} />
                        </div>
                      </td>
                      <td style={{ padding:"12px 16px", fontSize:13, fontWeight:600,
                        color:"var(--text-primary)", textAlign:"center" }}>
                        {c.total_jobs}
                      </td>
                      <td style={{ padding:"12px 16px", fontSize:13, fontWeight:600,
                        color:"var(--success-text)" }}>
                        {fmt(c.total_spend)}
                      </td>
                      <td style={{ padding:"12px 16px" }}>
                        {c.ltv_band && (
                          <Badge variant={c.ltv_band==="high"?"success":c.ltv_band==="medium"?"info":"muted"}
                            size="sm">{c.ltv_band}</Badge>
                        )}
                      </td>
                      <td style={{ padding:"12px 16px", fontSize:11, color:"var(--text-tertiary)" }}>
                        {c.last_job_at
                          ? new Date(c.last_job_at).toLocaleDateString("en-IN",
                              { day:"numeric", month:"short" })
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Pagination */}
          <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between",
            paddingTop:12, flexWrap:"wrap", gap:10 }}>
            <span style={{ fontSize:12, color:"var(--text-tertiary)" }}>
              {filtered.length} shown · {customers.data?.total ?? 0} total
            </span>
            <div style={{ display:"flex", gap:8 }}>
              {prevStack.length > 0 && (
                <Button variant="secondary" size="sm" onClick={handlePrev}>← Prev</Button>
              )}
              {customers.data?.has_next && (
                <Button variant="primary" size="sm" onClick={handleNext}>Next →</Button>
              )}
            </div>
          </div>
        </>
      )}
    </TenantLayout>
  );
}

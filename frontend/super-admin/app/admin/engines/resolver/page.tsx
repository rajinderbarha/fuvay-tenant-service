"use client";
import { useState, useCallback } from "react";
import Link from "next/link";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, CardHeader, SectionHeader, Badge, Btn, Skeleton } from "../../../../components/shared/ui";
import { useApi } from "../../../../hooks/useApi";
import { engineMgmtApi, catalogApi, adminTenantApi } from "../../../../lib/api";
import type {
  PlatformEngine, CategoryOption, AdminTenantRow, EngineAccessResolution,
} from "../../../../lib/api";
import { ArrowLeft, Zap, CheckCircle2, XCircle, Search } from "lucide-react";

const filterInput: React.CSSProperties = {
  height: 38, border: "1px solid var(--border)", borderRadius:"var(--radius-md)", fontSize: 13,
  padding: "0 10px", background: "var(--surface)", color: "var(--text-primary)",
  fontFamily: "inherit", outline: "none", width: "100%", boxSizing: "border-box",
};

// ── Generic searchable selector ──────────────────────────────────────────────
function SearchSelect<T>({
  value, label, placeholder, fetcher, renderOption, renderValue, onChange, onClear,
}: {
  value: T | null; label: string; placeholder: string;
  fetcher: (q: string) => Promise<T[]>;
  renderOption: (item: T) => React.ReactNode;
  renderValue: (item: T) => string;
  onChange: (item: T) => void;
  onClear: () => void;
}) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const opts = useApi(useCallback(() => fetcher(q), [q]), [q]);

  return (
    <div>
      <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>{label}</label>
      <div style={{ position: "relative" }}>
        <div style={{ position: "relative" }}>
          <Search size={13} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)", pointerEvents: "none" }} />
          <input
            value={open ? q : (value ? renderValue(value) : q)}
            onChange={e => { setQ(e.target.value); setOpen(true); }}
            onFocus={() => setOpen(true)}
            placeholder={placeholder}
            style={{ ...filterInput, paddingLeft: 30 }}
          />
        </div>
        {value && !open && (
          <button onClick={onClear} style={{
            position: "absolute", right: 8, top: "50%", transform: "translateY(-50%)",
            background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", fontSize: 12,
          }}>✕</button>
        )}
        {open && (
          <div style={{
            position: "absolute", top: "calc(100% + 4px)", left: 0, right: 0, zIndex: 20,
            background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-md)",
            boxShadow: "var(--shadow-md)", maxHeight: 260, overflowY: "auto",
          }}>
            {opts.loading && <div style={{ padding: 12, fontSize: 12, color: "var(--text-tertiary)" }}>Searching…</div>}
            {!opts.loading && (opts.data ?? []).map((item, i) => (
              <div key={i}
                onClick={() => { onChange(item); setOpen(false); setQ(""); }}
                style={{ padding: "9px 12px", cursor: "pointer", fontSize: 13, borderBottom: "1px solid var(--border)" }}
                onMouseEnter={e => (e.currentTarget.style.background = "var(--surface-sunken)")}
                onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
                {renderOption(item)}
              </div>
            ))}
            {!opts.loading && (opts.data ?? []).length === 0 && (
              <div style={{ padding: 12, fontSize: 12, color: "var(--text-tertiary)" }}>No matches.</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function EngineAccessResolverPage() {
  const [engine, setEngine] = useState<PlatformEngine | null>(null);
  const [category, setCategory] = useState<CategoryOption | null>(null);
  const [tenant, setTenant] = useState<AdminTenantRow | null>(null);

  const [result, setResult] = useState<EngineAccessResolution | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function resolve() {
    if (!engine) return;
    setLoading(true); setError(null); setResult(null);
    try {
      const res = await engineMgmtApi.resolveAccess({
        engine_key: engine.engine_key,
        tenant_id: tenant?.tenant_id,
        category_id: category?.id,
      });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to resolve access.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AdminLayout>
      <div style={{ marginBottom: 16 }}>
        <Link href="/admin/engines" style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 13, color: "var(--text-secondary)", textDecoration: "none" }}>
          <ArrowLeft size={14} /> Back to Engine Management
        </Link>
      </div>

      <SectionHeader
        title="Runtime Access Resolver"
        subtitle="Simulate the runtime access chain: Global → Category → Tenant Override → Runtime"
        icon={<Zap />}
      />

      <Card style={{ marginBottom: 20 }}>
        <CardHeader title="Resolve Access" subtitle="Engine is required; category and tenant are optional context" />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 14, marginBottom: 18 }}>
          <SearchSelect<PlatformEngine>
            value={engine} label="Engine (required)" placeholder="Search engine by name or key…"
            fetcher={async (q) => (await engineMgmtApi.list({ q: q || undefined, limit: 20 })).engines}
            renderOption={e => (
              <div>
                <div style={{ fontWeight: 600 }}>{e.display_name}</div>
                <div style={{ fontSize: 11, color: "var(--text-tertiary)", fontFamily: "monospace" }}>{e.engine_key}</div>
              </div>
            )}
            renderValue={e => `${e.display_name} (${e.engine_key})`}
            onChange={setEngine} onClear={() => setEngine(null)}
          />
          <SearchSelect<CategoryOption>
            value={category} label="Category (optional)" placeholder="Search category…"
            fetcher={async (q) => catalogApi.getCategoryOptions({ q: q || undefined })}
            renderOption={c => (
              <div>
                <div style={{ fontWeight: 600 }}>{c.name}</div>
                <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{c.slug} · {c.vertical_type ?? "—"}</div>
              </div>
            )}
            renderValue={c => c.name}
            onChange={setCategory} onClear={() => setCategory(null)}
          />
          <SearchSelect<AdminTenantRow>
            value={tenant} label="Tenant (optional)" placeholder="Search tenant by name…"
            fetcher={async (q) => (await adminTenantApi.list({ search: q || undefined, limit: 20 })).tenants}
            renderOption={t => (
              <div>
                <div style={{ fontWeight: 600 }}>{t.tenant_name}</div>
                <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{t.status} · {t.plan_type}</div>
              </div>
            )}
            renderValue={t => t.tenant_name}
            onChange={setTenant} onClear={() => setTenant(null)}
          />
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <Btn variant="success" onClick={resolve} disabled={!engine} loading={loading}>
            <Zap size={13} style={{ marginRight: 6 }} />Resolve Access
          </Btn>
        </div>
      </Card>

      {loading && (
        <Card>
          <Skeleton height={28} />
          <div style={{ marginTop: 8 }}><Skeleton height={28} /></div>
        </Card>
      )}

      {error && (
        <Card>
          <div style={{ padding: "14px 16px", background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius:"var(--radius-md)", fontSize: 13, color: "var(--danger-text)" }}>
            {error}
          </div>
        </Card>
      )}

      {!loading && result && (
        <Card>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
            {result.runtime_enabled
              ? <CheckCircle2 size={22} style={{ color: "var(--success)" }} />
              : <XCircle size={22} style={{ color: "var(--danger)" }} />}
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>
                {result.engine_key}
              </div>
              <Badge variant={result.runtime_enabled ? "success" : "danger"}>
                {result.runtime_enabled ? "Runtime Access Granted" : "Runtime Access Blocked"}
              </Badge>
            </div>
          </div>

          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", marginBottom: 8 }}>
              Resolution Path
            </div>
            {result.resolution_path.length === 0 && (
              <div style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No resolution steps recorded.</div>
            )}
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {result.resolution_path.map((step, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-primary)" }}>
                  <span style={{
                    width: 20, height: 20, borderRadius: "50%", background: "var(--success-bg)",
                    color: "var(--success)", display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 11, fontWeight: 700, flexShrink: 0,
                  }}>{i + 1}</span>
                  {step}
                </div>
              ))}
            </div>
          </div>

          {result.blockers.length > 0 && (
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: "var(--danger)", textTransform: "uppercase", marginBottom: 8 }}>
                Blockers
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {result.blockers.map((b, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 8, fontSize: 13, color: "var(--danger-text)", padding: "8px 12px", background: "var(--danger-bg)", borderRadius: 6 }}>
                    <XCircle size={14} style={{ flexShrink: 0, marginTop: 1 }} />
                    {b}
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {!loading && !result && !error && (
        <Card>
          <div style={{ padding: "40px 0", textAlign: "center", color: "var(--text-tertiary)", fontSize: 14 }}>
            Select an engine and click "Resolve Access" to trace the runtime access chain.
          </div>
        </Card>
      )}
    </AdminLayout>
  );
}

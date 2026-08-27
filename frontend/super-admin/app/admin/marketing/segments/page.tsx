"use client";
import { useState } from "react";
import { adminMarketingApi } from "@/lib/api";
import { PageHeader } from "@serviceos/design-system";

const card: React.CSSProperties = {
  background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", padding: 24,
};
const lbl: React.CSSProperties = { fontSize: 11, color: "var(--text-tertiary)", display: "block", marginBottom: 4 };
const inp: React.CSSProperties = {
  width: "100%", height: 36, padding: "0 12px", fontSize: 13, borderRadius:"var(--radius-md)",
  border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)",
  fontFamily: "inherit", boxSizing: "border-box",
};

export default function SegmentBuilderPage() {
  const [audience, setAudience]         = useState("customers");
  const [city, setCity]                 = useState("");
  const [hasAbandoned, setHasAbandoned] = useState(false);
  const [result, setResult]             = useState<any>(null);
  const [loading, setLoading]           = useState(false);

  async function preview() {
    setLoading(true);
    try {
      const rules: Record<string, unknown> = {};
      if (city) rules.city = city;
      if (hasAbandoned && audience === "customers") rules.has_abandoned_draft = true;
      const r = await adminMarketingApi.previewSegment({ audience, rules });
      setResult((r as any)?.data ?? null);
    } catch (e: any) {
      setResult({ error: e?.message });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <PageHeader
        title="Segment Builder"
        description="Preview your campaign audience before running a campaign."
        eyebrow="Marketing"
      />

      <div style={card}>
        <h2 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 16px" }}>Define Audience</h2>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(240px,1fr))", gap: 16, marginBottom: 16 }}>
          <div>
            <label style={lbl}>Target Audience</label>
            <select value={audience} onChange={e => setAudience(e.target.value)} style={inp}>
              <option value="customers">Customers</option>
              <option value="providers">Providers</option>
            </select>
          </div>
          <div>
            <label style={lbl}>City (optional)</label>
            <input type="text" value={city} onChange={e => setCity(e.target.value)}
              placeholder="e.g. Mumbai" style={inp} />
          </div>
        </div>

        {audience === "customers" && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
            <input type="checkbox" id="abandoned" checked={hasAbandoned}
              onChange={e => setHasAbandoned(e.target.checked)} />
            <label htmlFor="abandoned" style={{ fontSize: 13, color: "var(--text-primary)" }}>
              Has abandoned draft (booking, coaching, or real estate)
            </label>
          </div>
        )}

        <button onClick={preview} disabled={loading} style={{
          padding: "8px 20px", fontSize: 13, fontWeight: 600, borderRadius:"var(--radius-md)",
          border: "none", background: "var(--brand)", color: "white",
          cursor: loading ? "not-allowed" : "pointer", fontFamily: "inherit",
          opacity: loading ? 0.6 : 1,
        }}>
          {loading ? "Previewing…" : "Preview Segment"}
        </button>
      </div>

      {result && !result.error && (
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", padding: 20 }}>
          <h2 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 12px" }}>Preview Result</h2>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
            <div style={{ background: "var(--info-bg)", borderRadius:"var(--radius-md)", padding: 16 }}>
              <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Estimated Total</div>
              <div style={{ fontSize: 24, fontWeight: 600, color: "var(--accent)" }}>{result.estimated_total}</div>
            </div>
            <div style={{ background: "var(--surface-sunken)", borderRadius:"var(--radius-md)", padding: 16 }}>
              <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Preview Sample</div>
              <div style={{ fontSize: 24, fontWeight: 600, color: "var(--text-primary)" }}>{result.preview_count}</div>
            </div>
          </div>
          {result.preview_ids?.length > 0 && (
            <div>
              <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 6 }}>Sample IDs</div>
              <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, display: "flex", flexDirection: "column", gap: 4 }}>
                {result.preview_ids.map((id: string) => (
                  <div key={id} style={{ background: "var(--surface-sunken)", borderRadius: 4, padding: "4px 8px" }}>{id}</div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {result?.error && (
        <div style={{ background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius:"var(--radius-md)", padding: 16, fontSize: 13, color: "var(--danger-text)" }}>
          Error: {result.error}
        </div>
      )}
    </div>
  );
}

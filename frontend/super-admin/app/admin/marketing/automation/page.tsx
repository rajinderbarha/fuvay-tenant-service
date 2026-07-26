"use client";
import { useEffect, useState } from "react";
import { adminMarketingApi, AutomationTrigger } from "@/lib/api";

const card: React.CSSProperties = {
  background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", padding: 20,
};
const btnStyle: React.CSSProperties = {
  padding: "6px 12px", fontSize: 13, border: "1px solid var(--border)", borderRadius:"var(--radius-md)",
  background: "var(--surface)", color: "var(--text-secondary)", cursor: "pointer",
  fontFamily: "inherit", flexShrink: 0,
};

export default function AutomationTriggersPage() {
  const [triggers, setTriggers] = useState<AutomationTrigger[]>([]);
  const [loading, setLoading]   = useState(true);
  const [running, setRunning]   = useState<string | null>(null);
  const [results, setResults]   = useState<Record<string, any>>({});

  async function load() {
    setLoading(true);
    try {
      const r = await adminMarketingApi.listTriggers();
      setTriggers((r as any)?.data ?? []);
    } catch { setTriggers([]); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  async function runTrigger(trigger_key: string) {
    setRunning(trigger_key);
    try {
      const r = await adminMarketingApi.runTrigger(trigger_key);
      setResults(prev => ({ ...prev, [trigger_key]: (r as any)?.data }));
    } catch (e: any) {
      setResults(prev => ({ ...prev, [trigger_key]: { error: e?.message } }));
    } finally {
      setRunning(null);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <h1 style={{ fontSize: 22, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>Automation Triggers</h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
          Run triggers to send targeted notifications based on customer/provider behaviour.
          Cooldown windows prevent duplicate sends.
        </p>
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: "32px 0", color: "var(--text-tertiary)", fontSize: 13 }}>Loading triggers…</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {triggers.map(t => {
            const res = results[t.trigger_key];
            return (
              <div key={t.trigger_key} style={card}>
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)", textTransform: "capitalize" }}>
                      {t.trigger_key.replace(/_/g, " ")}
                    </div>
                    <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>{t.description}</div>
                    <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 4 }}>Cooldown: {t.cooldown_hours}h</div>
                    {res && !res.error && (
                      <div style={{ marginTop: 8, fontSize: 11, color: "var(--success-text)", background: "var(--success-bg)", borderRadius: 6, padding: "6px 12px" }}>
                        Targeted: {res.targeted} · Skipped (cooldown): {res.skipped}
                      </div>
                    )}
                    {res?.error && (
                      <div style={{ marginTop: 8, fontSize: 11, color: "var(--danger-text)", background: "var(--danger-bg)", borderRadius: 6, padding: "6px 12px" }}>
                        {res.error}
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => runTrigger(t.trigger_key)}
                    disabled={running === t.trigger_key}
                    style={{ ...btnStyle, opacity: running === t.trigger_key ? 0.5 : 1 }}
                  >
                    {running === t.trigger_key ? "Running…" : "Run Now"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

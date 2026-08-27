"use client";
import { TableSurface } from "@serviceos/design-system";
/**
 * Workspace Settings -- General tab. Dirty-field-tracked draft form over the
 * real composed read (workspaceSettingsApi.getGeneral) with explicit
 * per-field ownership from the backend -- editability is never inferred
 * from a field's key/name on the frontend.
 */
import React, { useEffect, useState } from "react";
import { Info, Lock, Clock3 } from "lucide-react";
import { Card, Badge } from "../shared/ui";
import { workspaceSettingsApi, type WorkspaceGeneralSettings, type WorkspaceSettingField } from "../../lib/api";

const inputStyle: React.CSSProperties = {
  width: "100%", padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border)",
  background: "var(--surface-sunken)", color: "var(--text-primary)", fontSize: 13, boxSizing: "border-box",
};
const lockedInputStyle: React.CSSProperties = {
  ...inputStyle, background: "var(--surface)", color: "var(--text-tertiary)", cursor: "not-allowed",
};

function ownershipIcon(ownership: string) {
  if (ownership === "TENANT_CONTROLLED" || ownership === "USER_CONTROLLED") return null;
  return <Lock size={11} style={{ color: "var(--text-tertiary)", marginLeft: 4 }}/>;
}

function FieldInput({ field, value, onChange }: {
  field: WorkspaceSettingField; value: string; onChange: (v: string) => void;
}) {
  return (
    <div>
      <label style={{ display: "flex", alignItems: "center", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>
        {field.label} {ownershipIcon(field.ownership)}
      </label>
      <input
        value={value}
        onChange={e => field.editable && onChange(e.target.value)}
        disabled={!field.editable}
        style={field.editable ? inputStyle : lockedInputStyle}
      />
      {field.help_text && <p style={{ fontSize: 10.5, color: "var(--text-tertiary)", margin: "4px 0 0" }}>{field.help_text}</p>}
    </div>
  );
}

export function GeneralTab({ onDirtyChange, saveRef }: {
  onDirtyChange: (dirty: boolean, meta: { save: () => Promise<void>; discard: () => void; count: number }) => void;
  saveRef?: React.MutableRefObject<(() => Promise<void>) | null>;
}) {
  const [data, setData] = useState<WorkspaceGeneralSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [saveError, setSaveError] = useState<string | null>(null);
  const [conflict, setConflict] = useState(false);

  async function load() {
    setLoading(true); setError(null);
    try {
      const res = await workspaceSettingsApi.getGeneral();
      setData(res);
      setDraft({});
    } catch {
      setError("Could not load workspace settings.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  function allFields(): WorkspaceSettingField[] {
    return data ? [...data.identity, ...data.regional] : [];
  }

  function fieldValue(key: string): string {
    if (key in draft) return draft[key];
    const f = allFields().find(x => x.key === key);
    return f ? String(f.value ?? "") : "";
  }

  function setField(key: string, value: string) {
    setDraft(d => ({ ...d, [key]: value }));
  }

  const dirtyKeys = Object.keys(draft).filter(k => {
    const f = allFields().find(x => x.key === k);
    return f && String(f.value ?? "") !== draft[k];
  });

  async function save() {
    if (!data) return;
    setSaveError(null); setConflict(false);
    try {
      const payload: Record<string, string> = {};
      for (const k of dirtyKeys) payload[k] = draft[k];
      const res = await workspaceSettingsApi.updateGeneral({ ...payload, expected_version: data.configuration_version });
      setData(res);
      setDraft({});
    } catch (e) {
      const err = e as { code?: string };
      if (err?.code === "SETTINGS_VERSION_STALE") setConflict(true);
      else setSaveError("Could not save changes.");
      throw e;
    }
  }

  function discard() {
    setDraft({});
  }

  useEffect(() => {
    onDirtyChange(dirtyKeys.length > 0, { save, discard, count: dirtyKeys.length });
    if (saveRef) saveRef.current = save;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dirtyKeys.length, data]);

  if (loading) return <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Loading…</p>;
  if (!data) return <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>{error ?? "Could not load workspace settings."}</p>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 900 }}>
      {conflict && (
        <div style={{ display: "flex", gap: 8, padding: "12px 14px", borderRadius: 8, background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
          <Info size={14} style={{ color: "var(--danger-text)", flexShrink: 0, marginTop: 1 }}/>
          <div>
            <p style={{ fontSize: 12.5, color: "var(--danger-text)", margin: "0 0 6px" }}>
              Workspace settings were changed by someone else since you loaded this page.
            </p>
            <button onClick={load} style={{ fontSize: 12, fontWeight: 700, color: "var(--danger-text)", background: "none", border: "none", cursor: "pointer", padding: 0 }}>
              Reload settings
            </button>
          </div>
        </div>
      )}
      {saveError && <p style={{ fontSize: 12, color: "var(--danger-text)" }}>{saveError}</p>}

      <Card>
        <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px" }}>Workspace identity</p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>
          {data.identity.map(f => (
            <FieldInput key={f.key} field={f} value={fieldValue(f.key)} onChange={v => setField(f.key, v)}/>
          ))}
        </div>
      </Card>

      <Card>
        <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px" }}>Regional preferences</p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>
          {data.regional.map(f => (
            f.key === "timezone" || f.key === "date_format" || f.key === "time_format" || f.key === "measurement_system" ? (
              <SelectField key={f.key} field={f} value={fieldValue(f.key)} onChange={v => setField(f.key, v)}/>
            ) : (
              <FieldInput key={f.key} field={f} value={fieldValue(f.key)} onChange={v => setField(f.key, v)}/>
            )
          ))}
        </div>
        <p style={{ fontSize: 10.5, color: "var(--text-tertiary)", marginTop: 10 }}>Locked by vertical policy where marked.</p>
      </Card>

      <Card>
        <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 8px", display: "flex", alignItems: "center", gap: 6 }}>
          <Clock3 size={14}/> Business hours
        </p>
        <div style={{ overflowX: "auto" }}>
          <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
            <thead>
              <tr>
                {data.business_hours.map(d => (
                  <th key={d.day_of_week} style={{ padding: "6px 8px", textAlign: "left", color: "var(--text-tertiary)", fontWeight: 600 }}>{d.day}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                {data.business_hours.map(d => (
                  <td key={d.day_of_week} style={{ padding: "6px 8px", color: d.is_open ? "var(--text-primary)" : "var(--text-tertiary)" }}>
                    {d.is_open ? `${d.start_time} – ${d.end_time}` : "Closed"}
                  </td>
                ))}
              </tr>
            </tbody>
          </TableSurface>
        </div>
        <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 10 }}>{data.business_hours_note}</p>
        <a href="/provider/availability" style={{ fontSize: 12, fontWeight: 600, color: "var(--brand)" }}>Edit business hours in Availability →</a>
      </Card>

      <div style={{ display: "flex", gap: 8, padding: "12px 16px", borderRadius: 8, background: "var(--surface-sunken)", border: "1px solid var(--border)" }}>
        <Info size={14} style={{ color: "var(--text-tertiary)", flexShrink: 0, marginTop: 1 }}/>
        <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Platform-controlled rules are shown for transparency and cannot be edited here.</span>
      </div>

      <Card>
        <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 14px" }}>Controlled by ServiceOS</p>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {data.controlled_policy.map(p => (
            <div key={p.key} style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{p.label}</span>
                  <Lock size={10} style={{ color: "var(--text-tertiary)" }}/>
                </div>
                <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "2px 0 0", maxWidth: 460 }}>{p.explanation}</p>
              </div>
              <div style={{ textAlign: "right", flexShrink: 0 }}>
                <Badge variant="muted" size="sm">{p.effective_value}</Badge>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function SelectField({ field, value, onChange }: { field: WorkspaceSettingField; value: string; onChange: (v: string) => void }) {
  const options: Record<string, string[]> = {
    timezone: ["Asia/Kolkata", "Asia/Dubai", "UTC"],
    date_format: ["DD MMM YYYY", "MM/DD/YYYY", "YYYY-MM-DD"],
    time_format: ["12-hour", "24-hour"],
    measurement_system: ["Metric", "Imperial"],
  };
  const opts = options[field.key] ?? [];
  return (
    <div>
      <label style={{ display: "flex", alignItems: "center", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>
        {field.label} {ownershipIcon(field.ownership)}
      </label>
      <select value={value} onChange={e => field.editable && onChange(e.target.value)} disabled={!field.editable}
        style={field.editable ? inputStyle : lockedInputStyle}>
        {!opts.includes(value) && value && <option value={value}>{value}</option>}
        {opts.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
      {field.help_text && <p style={{ fontSize: 10.5, color: "var(--text-tertiary)", margin: "4px 0 0" }}>{field.help_text}</p>}
    </div>
  );
}

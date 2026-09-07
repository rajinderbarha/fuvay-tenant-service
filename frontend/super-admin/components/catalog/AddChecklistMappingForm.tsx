"use client";
import React, { useCallback, useEffect, useState } from "react";
import { checklistCatalogApi, type ChecklistPurpose, type ChecklistUsage, type ChecklistActor, type ChecklistCompletionGate } from "../../lib/api";
import { useApi, useAction } from "../../hooks/useApi";
import { CHECKLIST_GATES, CHECKLIST_PURPOSES, checklistLabel } from "./checklist-config";

export function AddChecklistMappingForm({ masterServiceJobTypeId, onAdded, onError }: {
  masterServiceJobTypeId: string;
  onAdded: () => void; onError: (msg: string) => void;
}) {
  const [mode, setMode] = useState<"existing" | "new">("existing");
  const [versionId, setVersionId] = useState("");
  const [templateQuery, setTemplateQuery] = useState("");
  const [debouncedTemplateQuery, setDebouncedTemplateQuery] = useState("");
  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedTemplateQuery(templateQuery.trim()), 250);
    return () => window.clearTimeout(timer);
  }, [templateQuery]);
  const templatesApi = useApi(useCallback(
    () => checklistCatalogApi.listPublishedTemplateOptions(debouncedTemplateQuery, 50),
    [debouncedTemplateQuery]), [debouncedTemplateQuery]);
  const publishedTemplates = templatesApi.data ?? [];
  const [phase, setPhase] = useState("inspection");
  const [usage, setUsage] = useState<ChecklistUsage>("REQUIRED");
  const [actor, setActor] = useState<ChecklistActor>("TECHNICIAN");
  const [gate, setGate] = useState<ChecklistCompletionGate>("NONE");
  const [newName, setNewName] = useState("");
  const [newItemLabel, setNewItemLabel] = useState("");
  const [newCode, setNewCode] = useState("");
  const [purpose, setPurpose] = useState<ChecklistPurpose>("INSPECTION");
  const selectedPurpose = mode === "new" ? purpose : publishedTemplates.find(row => row.latest_version?.id === versionId)?.purpose;
  const allowedGates = selectedPurpose ? CHECKLIST_GATES[selectedPurpose] : ["NONE" as ChecklistCompletionGate];
  useEffect(() => { if (!allowedGates.includes(gate)) setGate("NONE"); }, [selectedPurpose]);
  const create = useAction(useCallback(async (vId: string) => {
    try {
      return await checklistCatalogApi.createMapping({
        master_service_job_type_id: masterServiceJobTypeId, checklist_template_version_id: vId,
        phase, usage, actor, completion_gate: gate,
      });
    } catch (error) {
      onError(error instanceof Error ? error.message : "Couldn't map this checklist.");
      throw error;
    }
  }, [masterServiceJobTypeId, phase, usage, actor, gate, onError]));
  const quickCreate = useAction(useCallback(async () => {
    const code = newCode.trim() || newName.trim().toUpperCase().replace(/[^A-Z0-9]+/g, "_").slice(0, 60);
    return checklistCatalogApi.quickCreateMapping({ name: newName.trim(), code, purpose,
      items: newItemLabel.split("\n").map(value => value.trim()).filter(Boolean),
      master_service_job_type_id: masterServiceJobTypeId, phase, usage, actor, completion_gate: gate,
    });
  }, [newName, newCode, newItemLabel, purpose, masterServiceJobTypeId, phase, usage, actor, gate]));

  async function submit() {
    if (!versionId) return;
    const result = await create.execute(versionId);
    if (result) onAdded();
  }

  async function submitNew() {
    if (!newName.trim()) return;
    const result = await quickCreate.execute();
    if (result) onAdded();
  }

  const smallSelect: React.CSSProperties = { fontSize: 12, padding: "6px 8px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)" };

  return (
    <div style={{ marginBottom: 14, padding: 12, borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--surface-sunken)", display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ display: "flex", gap: 6 }}>
        <button onClick={() => setMode("existing")} style={{ fontSize: 11, fontWeight: 600, padding: "4px 10px", borderRadius: 999, border: "1px solid var(--border)", background: mode === "existing" ? "var(--brand)" : "var(--surface)", color: mode === "existing" ? "white" : "var(--text-secondary)", cursor: "pointer" }}>Use existing</button>
        <button onClick={() => setMode("new")} style={{ fontSize: 11, fontWeight: 600, padding: "4px 10px", borderRadius: 999, border: "1px solid var(--border)", background: mode === "new" ? "var(--brand)" : "var(--surface)", color: mode === "new" ? "white" : "var(--text-secondary)", cursor: "pointer" }}>Create new</button>
      </div>

      {mode === "existing" ? (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          <input value={templateQuery} onChange={event => { setTemplateQuery(event.target.value); setVersionId(""); }} placeholder="Search published checklists" style={smallSelect}/>
          <select aria-label="Published checklist" disabled={templatesApi.loading} value={versionId} onChange={e => setVersionId(e.target.value)} style={{ ...smallSelect, flex: "1 1 240px", minWidth: 0 }}>
          <option value="">— Select published checklist —</option>
            {publishedTemplates.map(t => <option key={t.id} value={t.latest_version!.id}>{t.name} (v{t.latest_version!.version_number})</option>)}
          </select>
        </div>
      ) : (
        <>
          <input aria-label="Checklist name" maxLength={200} value={newName} onChange={e => setNewName(e.target.value)} placeholder="New checklist name (e.g. Pre-Installation Safety Check)" style={{ ...smallSelect, width: "100%", boxSizing: "border-box" }}/>
          <input aria-label="Checklist code" value={newCode} onChange={e => setNewCode(e.target.value.toUpperCase())} placeholder="Code (generated from name if blank)" style={smallSelect}/>
          <label>Checklist purpose<select aria-label="Checklist purpose" value={purpose} onChange={event => { setPurpose(event.target.value as ChecklistPurpose); setPhase(event.target.value.toLowerCase()); }} style={smallSelect}>{CHECKLIST_PURPOSES.map(value => <option key={value} value={value}>{checklistLabel(value)}</option>)}</select></label>
          <textarea aria-label="Checklist points" value={newItemLabel} onChange={e => setNewItemLabel(e.target.value)} rows={6} placeholder="Checklist points — one per line. Example: Power supply verified" style={{ ...smallSelect, width: "100%", boxSizing: "border-box" }}/>
          <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>Each line becomes a required checkbox item. Create & Map publishes the checklist and attaches it to this exact job type. Use the Checklist Library for sections, photos, measurements and other answer types.</p>
        </>
      )}

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <select aria-label="Checklist phase" value={phase} onChange={e => setPhase(e.target.value)} style={smallSelect}>{CHECKLIST_PURPOSES.map(value => <option key={value} value={value.toLowerCase()}>{checklistLabel(value)}</option>)}</select>
        <select aria-label="Checklist usage" value={usage} onChange={e => setUsage(e.target.value as ChecklistUsage)} style={smallSelect}>
          <option value="DISABLED">DISABLED</option><option value="OPTIONAL">OPTIONAL</option><option value="REQUIRED">REQUIRED</option>
        </select>
        <select aria-label="Assigned actor" value={actor} onChange={e => setActor(e.target.value as ChecklistActor)} style={smallSelect}>
          <option value="TECHNICIAN">TECHNICIAN</option><option value="STAFF">STAFF</option><option value="TENANT_ADMIN">TENANT_ADMIN</option><option value="CUSTOMER">CUSTOMER</option>
        </select>
        <select aria-label="Completion gate" value={gate} onChange={e => setGate(e.target.value as ChecklistCompletionGate)} style={smallSelect}>
          {allowedGates.map(value => <option key={value} value={value}>{checklistLabel(value)}</option>)}
        </select>
      </div>
      {(create.error || quickCreate.error || templatesApi.error) && <p role="alert" style={{ color: "var(--danger-text)" }}>{create.error || quickCreate.error || templatesApi.error}</p>}
      {mode === "existing" ? (
        <button onClick={submit} disabled={!versionId || templatesApi.loading || create.loading}
          style={{ alignSelf: "flex-start", fontSize: 12, fontWeight: 700, padding: "6px 14px", borderRadius: 8, border: "none", background: "var(--brand)", color: "white", cursor: !versionId || create.loading ? "default" : "pointer" }}>
          {create.loading ? "Mapping…" : "Map Checklist"}
        </button>
      ) : (
        <button onClick={submitNew} disabled={!newName.trim() || !newItemLabel.trim() || quickCreate.loading || create.loading}
          style={{ alignSelf: "flex-start", fontSize: 12, fontWeight: 700, padding: "6px 14px", borderRadius: 8, border: "none", background: "var(--brand)", color: "white", cursor: !newName.trim() || quickCreate.loading || create.loading ? "default" : "pointer" }}>
          {quickCreate.loading || create.loading ? "Creating…" : "Create & Map"}
        </button>
      )}
    </div>
  );
}

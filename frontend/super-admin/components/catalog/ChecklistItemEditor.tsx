"use client";
import React, { useState } from "react";
import { Btn, Modal } from "../shared/ui";
import { checklistCatalogApi, type ChecklistItemRow, type ChecklistItemType } from "../../lib/api";
import { useAction } from "../../hooks/useApi";

const TYPES: ChecklistItemType[] = ["CHECKBOX", "YES_NO", "SHORT_TEXT", "LONG_TEXT", "NUMBER", "MEASUREMENT", "SINGLE_SELECT", "MULTI_SELECT", "PHOTO", "DOCUMENT", "SIGNATURE"];
const input: React.CSSProperties = { width: "100%", padding: "9px 11px", border: "1px solid var(--border)", borderRadius: 8, background: "var(--surface)", color: "var(--text-primary)", boxSizing: "border-box" };

export function ChecklistItemEditor({ sectionId, item, order = 0, onSaved }: {
  sectionId: string; item?: ChecklistItemRow; order?: number; onSaved: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [label, setLabel] = useState(item?.label ?? "");
  const [type, setType] = useState<ChecklistItemType>(item?.item_type ?? "CHECKBOX");
  const [help, setHelp] = useState(item?.help_text ?? "");
  const [required, setRequired] = useState(item?.is_required ?? true);
  const [evidence, setEvidence] = useState(item?.evidence_required ?? false);
  const [visible, setVisible] = useState(item?.customer_visible ?? false);
  const [unit, setUnit] = useState(item?.measurement_unit ?? "");
  const [choices, setChoices] = useState((item?.select_options ?? []).map(option => option.label).join("\n"));
  const [minimum, setMinimum] = useState(item?.min_evidence_count ?? 1);
  const [maximum, setMaximum] = useState(item?.max_evidence_count ?? 1);
  const [removeOpen, setRemoveOpen] = useState(false);
  const hasEvidence = ["PHOTO", "DOCUMENT", "SIGNATURE"].includes(type);
  const hasChoices = ["SINGLE_SELECT", "MULTI_SELECT"].includes(type);
  const options = [...new Set(choices.split("\n").map(value => value.trim()).filter(Boolean))];
  const save = useAction(async () => {
    const payload = {
      item_type: type, label: label.trim(), help_text: help.trim() || null, is_required: required,
      evidence_required: hasEvidence && evidence, customer_visible: visible,
      min_evidence_count: hasEvidence ? minimum : 0, max_evidence_count: hasEvidence ? maximum : 1,
      measurement_unit: type === "MEASUREMENT" ? unit.trim() || null : null,
      select_options: hasChoices ? options.map(value => ({
        // Keep existing values stable when only a label/order is unchanged.
        value: item?.select_options?.find(option => option.label === value)?.value ?? value, label: value,
      })) : null,
    };
    if (item) await checklistCatalogApi.updateItem(item.id, payload);
    else await checklistCatalogApi.addItem(sectionId, { ...payload, display_order: order });
    setOpen(false); onSaved();
    if (!item) { setLabel(""); setHelp(""); setChoices(""); }
  });
  const remove = useAction(async () => { if (item) await checklistCatalogApi.deleteItem(item.id); setRemoveOpen(false); onSaved(); });
  return <>
    <Btn size="xs" variant="secondary" onClick={() => { save.clearError(); setOpen(true); }}>{item ? "Edit item" : "+ Add item"}</Btn>
    {item && <Btn size="xs" variant="ghost" onClick={() => setRemoveOpen(true)}>Remove</Btn>}
    <Modal open={open} onClose={() => { if (!save.loading) setOpen(false); }} title={item ? "Edit draft checklist item" : "Add checklist item"} size="lg">
      <div style={{ display: "grid", gap: 14 }}>
        <label>Item label<input aria-label="Item label" maxLength={300} style={input} value={label} onChange={event => setLabel(event.target.value)}/></label>
        <label>Answer type<select aria-label="Answer type" style={input} value={type} onChange={event => { setType(event.target.value as ChecklistItemType); setEvidence(false); }}>
          {TYPES.map(value => <option key={value} value={value}>{value.replaceAll("_", " ").toLowerCase()}</option>)}
        </select></label>
        <label>Instructions (optional)<textarea aria-label="Item instructions" style={input} value={help} onChange={event => setHelp(event.target.value)} rows={2}/></label>
        {hasChoices && <label>Choices — one per line<textarea aria-label="Choices" style={input} rows={4} value={choices} onChange={event => setChoices(event.target.value)}/><small>At least two distinct choices are required.</small></label>}
        {type === "MEASUREMENT" && <label>Measurement unit<input aria-label="Measurement unit" style={input} maxLength={30} value={unit} onChange={event => setUnit(event.target.value)}/></label>}
        <label><input type="checkbox" checked={required} onChange={event => setRequired(event.target.checked)}/> Required to complete this checklist</label>
        <label><input type="checkbox" checked={visible} onChange={event => setVisible(event.target.checked)}/> Visible to the customer</label>
        {hasEvidence && <>
          <label><input type="checkbox" checked={evidence} onChange={event => setEvidence(event.target.checked)}/> Require uploaded evidence</label>
          <div style={{ display: "flex", gap: 12 }}>
            <label>Minimum files<input aria-label="Minimum evidence files" type="number" min={0} style={input} value={minimum} onChange={event => setMinimum(Number(event.target.value))}/></label>
            <label>Maximum files<input aria-label="Maximum evidence files" type="number" min={1} style={input} value={maximum} onChange={event => setMaximum(Number(event.target.value))}/></label>
          </div>
        </>}
        {save.error && <p role="alert" style={{ color: "var(--danger-text)" }}>{save.error}</p>}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <Btn variant="ghost" disabled={save.loading} onClick={() => setOpen(false)}>Cancel</Btn>
          <Btn variant="primary" loading={save.loading} disabled={!label.trim() || (hasChoices && options.length < 2) || (hasEvidence && (minimum < 0 || maximum < Math.max(minimum, 1)))} onClick={() => save.execute()}>Save item</Btn>
        </div>
      </div>
    </Modal>
    <Modal open={removeOpen} onClose={() => setRemoveOpen(false)} title="Remove draft item?">
      <p>This removes “{item?.label}” from this draft only. Published versions and existing jobs stay unchanged.</p>
      {remove.error && <p role="alert">{remove.error}</p>}
      <Btn variant="danger" loading={remove.loading} onClick={() => remove.execute()}>Remove draft item</Btn>
    </Modal>
  </>;
}

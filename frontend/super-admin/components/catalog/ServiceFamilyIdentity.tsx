"use client";
import React, { useEffect, useState } from "react";
import { catalogApi } from "../../lib/api";
import { useAction } from "../../hooks/useApi";
import { Btn, Input } from "../shared/ui";
import { namedJobType } from "./service-family";

export function ServiceFamilyIdentity({ serviceId, name, canWrite, onSaved }: {
  serviceId: string; name: string; canWrite: boolean; onSaved: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(name);
  useEffect(() => { setValue(name); setEditing(false); }, [serviceId, name]);
  const save = useAction(async () => {
    if (!value.trim() || value.trim() === name) return;
    await catalogApi.updateMasterService(serviceId, { service_name: value.trim() });
    setEditing(false);
    onSaved();
  });
  if (!namedJobType(name) && !editing) return null;
  return <section aria-label="Service family naming" style={{ marginTop: 12, padding: 12, background: "var(--warning-bg)", color: "var(--warning-text)", borderRadius: 8 }}>
    <p>This name describes a specific job. If you offer several job types, name the family “Air Conditioner”, with Installation and Repair below it. Do not create another family for each task.</p>
    <p>Renaming changes this catalog label only. It does not merge duplicate families, remove job types, change provider prices or rewrite past jobs.</p>
    {!editing && canWrite && <Btn size="sm" variant="secondary" onClick={() => setEditing(true)}>Edit family name</Btn>}
    {editing && <>
      <Input label="Service family name" value={value} onChange={setValue} disabled={save.loading} placeholder="e.g. Air Conditioner" />
      {save.error && <p role="alert">{save.error}</p>}
      <Btn size="sm" disabled={!value.trim() || value.trim() === name || save.loading} onClick={() => save.execute()}>Save family name</Btn>
      <Btn size="sm" variant="secondary" disabled={save.loading} onClick={() => { setValue(name); setEditing(false); }}>Cancel</Btn>
    </>}
  </section>;
}

"use client";
import React, { useCallback, useState } from "react";
import { catalogWorkspaceApi } from "../../lib/api";
import { useApi, useAction } from "../../hooks/useApi";
import { Btn, Select } from "../shared/ui";

export function AddServiceJobType({ masterServiceId, linkedJobTypeIds, onAdded, onError }: {
  masterServiceId: string; linkedJobTypeIds: string[];
  onAdded: () => void; onError: (message: string) => void;
}) {
  const [pickedId, setPickedId] = useState("");
  const types = useApi(useCallback(() => catalogWorkspaceApi.listJobTypes({ pageSize: 100 }), []), []);
  const action = useAction(catalogWorkspaceApi.addServiceJobType);
  const available = (types.data?.items ?? []).filter(type => type.is_active && type.runtime_supported && !linkedJobTypeIds.includes(type.id));
  async function attach() {
    if (!available.some(type => type.id === pickedId)) return;
    const result = await action.execute(masterServiceId, pickedId);
    if (result) { setPickedId(""); onAdded(); }
    else onError("Could not add the job type. Check the error below.");
  }
  return <section aria-label="Add a supported job type" style={{ marginTop: 12, padding: 14, border: "1px solid var(--border)", borderRadius: 10 }}>
    <p>Choose the work offered under this service family. Example: Air Conditioner → Installation. Configure requirements in that job type’s blueprint, not here.</p>
    {types.error && <p role="alert">{types.error} <button onClick={types.refetch}>Retry</button></p>}
    {action.error && <p role="alert">{action.error}</p>}
    <Select label="Job type" value={pickedId} onChange={setPickedId} disabled={types.loading || action.loading}
      options={[{ value: "", label: types.loading ? "Loading job types…" : "Select job type" }, ...available.map(type => ({ value: type.id, label: type.label }))]} />
    {!types.loading && !types.error && !available.length && <p>All available supported job types are already attached.</p>}
    <Btn disabled={!available.some(type => type.id === pickedId) || action.loading} onClick={attach}>Add job type</Btn>
    <p style={{ fontSize: 12, color: "var(--text-secondary)" }}>Only job types supported by booking and technician workflows are offered. Custom runtime development is not a catalog setup step.</p>
  </section>;
}

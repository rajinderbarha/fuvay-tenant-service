"use client";
import React, { useCallback, useState, useEffect } from "react";
import { StaffLayout } from "../../../components/layout/StaffLayout";
import { Card, Input, Btn, Skeleton, Badge } from "../../../components/shared/ui";
import { useApi, useAction } from "../../../hooks/useApi";
import { authApi } from "../../../lib/api";

export default function StaffProfilePage() {
  const me = useApi(useCallback(() => authApi.me(), []));
  const [fullName, setFullName] = useState("");
  const [editing, setEditing] = useState(false);

  useEffect(() => { if (me.data) setFullName(me.data.full_name || ""); }, [me.data]);

  const saveAction = useAction(
    () => authApi.updateMe({ full_name: fullName }),
    { onSuccess: () => { setEditing(false); me.refetch(); } }
  );

  return (
    <StaffLayout activeNav="profile">
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>My Profile</h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
          Update your own contact details. Role, tenant, and verification status are managed by your tenant admin.
        </p>
      </div>

      {me.loading ? <Skeleton height={300}/> : me.error ? (
        <Card><p style={{ color: "var(--danger-text)", fontSize: 13 }}>{me.error}{me.requestId && ` — Request ID: ${me.requestId}`}</p></Card>
      ) : (
        <Card style={{ maxWidth: 520 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {editing ? (
              <Input label="Full Name" value={fullName} onChange={setFullName}/>
            ) : (
              <ReadField label="Name" value={me.data?.full_name}/>
            )}
            <ReadField label="Email" value={me.data?.email} note="readonly"/>
            <ReadField label="Role" value={me.data?.role} note="readonly"/>
            <ReadField label="Tenant" value={me.data?.tenant_id} note="readonly"/>
            <div>
              <div style={{ fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", marginBottom: 4 }}>Verification Status</div>
              <Badge variant="muted" size="sm">Managed by admin — self-verification not available</Badge>
            </div>

            {saveAction.error && (
              <p style={{ fontSize: 12, color: "var(--danger-text)" }}>
                {saveAction.error}{saveAction.requestId && ` — Request ID: ${saveAction.requestId}`}
              </p>
            )}

            <div style={{ display: "flex", gap: 8 }}>
              {editing ? (
                <>
                  <Btn size="sm" onClick={() => saveAction.execute()}>{saveAction.loading ? "Saving…" : "Save"}</Btn>
                  <Btn size="sm" variant="secondary" onClick={() => { setEditing(false); setFullName(me.data?.full_name || ""); }}>Cancel</Btn>
                </>
              ) : (
                <Btn size="sm" onClick={() => setEditing(true)}>Edit Profile</Btn>
              )}
            </div>
          </div>
        </Card>
      )}
    </StaffLayout>
  );
}

function ReadField({ label, value, note }: { label: string; value?: string | null; note?: string }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", marginBottom: 4 }}>
        {label}{note && <span style={{ fontStyle: "italic" }}> ({note})</span>}
      </div>
      <div style={{ fontSize: 14 }}>{value || "—"}</div>
    </div>
  );
}

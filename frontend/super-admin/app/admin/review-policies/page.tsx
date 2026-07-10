"use client";
import { useCallback, useState } from "react";
import { adminPolicyApi, type ReviewPolicyRecord } from "../../../lib/api";
import { Card, Badge, Btn, Skeleton, Toaster, type ToastItem } from "../../../components/shared/ui";
import { useApi, useAction } from "../../../hooks/useApi";
import { Shield, RefreshCw, Save } from "lucide-react";

export default function AdminReviewPoliciesPage() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const addToast = useCallback((title: string, variant: ToastItem["variant"] = "success") => {
    const id = Math.random().toString(36).slice(2);
    setToasts(prev => [...prev, { id, title, variant }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 3500);
  }, []);

  const [editing, setEditing] = useState<string | null>(null);
  const [editData, setEditData] = useState<Partial<ReviewPolicyRecord>>({});

  const { data, loading, refetch } = useApi(useCallback(() => adminPolicyApi.list(), []));
  const policies: ReviewPolicyRecord[] = (Array.isArray(data) ? data : []) as ReviewPolicyRecord[];

  const updateAction = useAction(
    useCallback((id: string, body: Partial<ReviewPolicyRecord>) => adminPolicyApi.update(id, body), [])
  );

  const handleSave = async (id: string) => {
    const result = await updateAction.execute(id, editData);
    if (result) {
      addToast("Policy updated.", "success");
      setEditing(null);
      setEditData({});
      refetch();
    } else {
      addToast(updateAction.error ?? "Update failed.", "danger");
    }
  };

  return (
    <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 24, maxWidth: 900 }}>
      <Toaster toasts={toasts} onRemove={id => setToasts(p => p.filter(t => t.id !== id))} />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: 0,
            display: "flex", alignItems: "center", gap: 10 }}>
            <Shield size={22} /> Review Policies
          </h1>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "6px 0 0" }}>
            Configure moderation rules and eligibility settings for reviews.
          </p>
        </div>
        <Btn variant="ghost" onClick={refetch}><RefreshCw size={14} /> Refresh</Btn>
      </div>

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {[0,1].map(i => <Skeleton key={i} height={140} />)}
        </div>
      ) : policies.length === 0 ? (
        <Card padding={48} style={{ textAlign: "center" }}>
          <Shield size={32} style={{ color: "var(--text-tertiary)", margin: "0 auto 12px" }} />
          <p style={{ color: "var(--text-secondary)", margin: 0 }}>No policies configured.</p>
        </Card>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {policies.map((p: ReviewPolicyRecord) => (
            <Card key={p.id} padding={18}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                <div>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <p style={{ fontWeight: 600, fontSize: 14, color: "var(--text-primary)", margin: 0 }}>
                      {p.policy_name}
                    </p>
                    <Badge variant={p.is_active ? "success" : "default"}>{p.is_active ? "Active" : "Inactive"}</Badge>
                  </div>
                  <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "4px 0 0" }}>
                    Key: {p.policy_key}
                  </p>
                </div>
                <Btn size="sm" variant="ghost" onClick={() => {
                  setEditing(p.id);
                  setEditData({
                    auto_approve_enabled: p.auto_approve_enabled,
                    require_admin_moderation: p.require_admin_moderation,
                    allow_provider_reply: p.allow_provider_reply,
                    require_reply_moderation: p.require_reply_moderation,
                    allow_review_edit: p.allow_review_edit,
                    edit_window_hours: p.edit_window_hours,
                  });
                }}>Edit</Btn>
              </div>

              {editing === p.id ? (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  {[
                    ["auto_approve_enabled", "Auto Approve"],
                    ["require_admin_moderation", "Require Moderation"],
                    ["allow_provider_reply", "Allow Provider Reply"],
                    ["require_reply_moderation", "Moderate Replies"],
                    ["allow_review_edit", "Allow Edit"],
                  ].map(([key, label]) => (
                    <label key={key} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
                      <input
                        type="checkbox"
                        checked={!!(editData as Record<string, unknown>)[key]}
                        onChange={e => setEditData(d => ({ ...d, [key]: e.target.checked }))}
                      />
                      {label}
                    </label>
                  ))}
                  <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, gridColumn: "span 2" }}>
                    Edit Window (hours):
                    <input
                      type="number"
                      value={editData.edit_window_hours ?? p.edit_window_hours}
                      onChange={e => setEditData(d => ({ ...d, edit_window_hours: parseInt(e.target.value) }))}
                      style={{ padding: "4px 8px", borderRadius: 4, border: "1px solid var(--border)",
                        background: "var(--surface)", fontSize: 13, width: 80 }}
                    />
                  </label>
                  <div style={{ gridColumn: "span 2", display: "flex", gap: 8, marginTop: 4 }}>
                    <Btn size="sm" onClick={() => handleSave(p.id)} loading={updateAction.loading}>
                      <Save size={12} /> Save
                    </Btn>
                    <Btn size="sm" variant="ghost" onClick={() => { setEditing(null); setEditData({}); }}>Cancel</Btn>
                  </div>
                </div>
              ) : (
                <div style={{ display: "flex", gap: 12, fontSize: 12, color: "var(--text-tertiary)", flexWrap: "wrap" }}>
                  <span>Auto-approve: {p.auto_approve_enabled ? "Yes" : "No"}</span>
                  <span>Moderation: {p.require_admin_moderation ? "Required" : "Optional"}</span>
                  <span>Provider Reply: {p.allow_provider_reply ? "Allowed" : "Disabled"}</span>
                  <span>Edit Window: {p.edit_window_hours}h</span>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

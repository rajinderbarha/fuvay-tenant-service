"use client";
import { useCallback, useState } from "react";
import { adminFlagApi, type ReviewFlagRecord } from "../../../lib/api";
import { Card, Badge, Btn, Skeleton, Toaster, SectionHeader, type ToastItem } from "../../../components/shared/ui";
import { useApi, useAction } from "../../../hooks/useApi";
import { Flag, RefreshCw, CheckCircle } from "lucide-react";

function flagVariant(s: string): "danger"|"warning"|"success" {
  if (s === "open")     return "danger";
  if (s === "reviewed") return "warning";
  return "success";
}

export default function AdminReviewFlagsPage() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const addToast = useCallback((title: string, variant: ToastItem["variant"] = "success") => {
    const id = Math.random().toString(36).slice(2);
    setToasts(prev => [...prev, { id, title, variant }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 3500);
  }, []);

  const { data, loading, refetch } = useApi(
    useCallback(() => adminFlagApi.list("open"), [])
  );
  const flags: ReviewFlagRecord[] = (Array.isArray(data) ? data : []) as ReviewFlagRecord[];

  const resolveAction = useAction(useCallback((flagId: string) => adminFlagApi.resolve(flagId), []));

  const handleResolve = async (flagId: string) => {
    const result = await resolveAction.execute(flagId);
    if (result) { addToast("Flag resolved.", "success"); refetch(); }
    else { addToast(resolveAction.error ?? "Failed to resolve.", "danger"); }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--layout-page-gap)" }}>
      <Toaster toasts={toasts} onRemove={id => setToasts(p => p.filter(t => t.id !== id))} />

      <SectionHeader eyebrow="Trust & quality" title="Review Flags"
        description="Open flags from customers or providers that require moderation." icon={<Flag />}
        actions={<Btn variant="ghost" onClick={refetch}><RefreshCw size={14} /> Refresh</Btn>} />

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {[0,1,2].map(i => <Skeleton key={i} height={80} />)}
        </div>
      ) : flags.length === 0 ? (
        <Card padding={48} style={{ textAlign: "center" }}>
          <Flag size={32} style={{ color: "var(--text-tertiary)", margin: "0 auto 12px" }} />
          <p style={{ color: "var(--text-secondary)", margin: 0 }}>No open flags.</p>
        </Card>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {flags.map((f: ReviewFlagRecord) => (
            <Card key={f.id} padding={14}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
                <div>
                  <div style={{ display: "flex", gap: 8, marginBottom: 6 }}>
                    <Badge variant={flagVariant(f.status)}>{f.status}</Badge>
                    <Badge variant="default">{f.reason_code}</Badge>
                    <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>by {f.flagged_by_type}</span>
                  </div>
                  <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
                    {f.reason_text ?? "No description provided."}
                  </p>
                  <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "4px 0 0" }}>
                    Review: {f.review_id?.slice(0, 8)} · {f.created_at ? new Date(f.created_at).toLocaleString() : "—"}
                  </p>
                </div>
                <Btn size="sm" onClick={() => handleResolve(f.id)} loading={resolveAction.loading}>
                  <CheckCircle size={12} /> Resolve
                </Btn>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

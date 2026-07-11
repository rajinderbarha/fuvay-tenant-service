"use client";
/**
 * FINAL-L5-04B — Admin Tenant Entitlement Management.
 * Assign/disable/re-enable module + category entitlements for one tenant.
 * Refreshes the sidebar's vertical-catalog cache after every mutation via
 * useAdminMenuRefresh() (same live-refresh pattern as FINAL-L5-04's
 * /admin/verticals and /admin/categories fixes).
 */
import React, { useState, useCallback } from "react";
import { Card, Badge, Btn, Skeleton } from "../shared/ui";
import { adminEntitlementApi } from "../../lib/api";
import { useApi, useAction } from "../../hooks/useApi";
import { useAdminMenuRefresh } from "../layout/AdminLayout";
import { RefreshCw, CheckCircle2, XCircle, History } from "lucide-react";

function StatusBadge({ status }: { status: string }) {
  const variant = status === "ACTIVE" ? "success" : status === "PENDING" ? "warning" : "default";
  return <Badge variant={variant as never}>{status}</Badge>;
}

export function EntitlementsTab({ tenantId }: { tenantId: string }) {
  const refreshMenu = useAdminMenuRefresh();
  const [showHistory, setShowHistory] = useState(false);

  const entApi = useApi(useCallback(() => adminEntitlementApi.get(tenantId), [tenantId]), [tenantId]);
  const historyApi = useApi(useCallback(() => adminEntitlementApi.getHistory(tenantId), [tenantId]), [tenantId]);

  const disableModule = useAction((moduleKey: string) => adminEntitlementApi.disableModule(tenantId, moduleKey, "disabled via admin UI"));
  const reenableModule = useAction((moduleKey: string) => adminEntitlementApi.reenableModule(tenantId, moduleKey));
  const disableCategory = useAction((categoryId: string) => adminEntitlementApi.disableCategory(tenantId, categoryId, "disabled via admin UI"));
  const reenableCategory = useAction((categoryId: string) => adminEntitlementApi.reenableCategory(tenantId, categoryId));

  async function afterMutation() {
    await entApi.refetch();
    await historyApi.refetch();
    refreshMenu();
  }

  if (entApi.loading) return <Skeleton height={200}/>;

  const modules = entApi.data?.modules ?? [];
  const categories = entApi.data?.categories ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
          {modules.length} module{modules.length !== 1 ? "s" : ""}, {categories.length} categor{categories.length !== 1 ? "ies" : "y"} — effective entitlements only
        </p>
        <div style={{ display: "flex", gap: 8 }}>
          <Btn size="sm" variant="ghost" icon={<History size={13}/>} onClick={() => setShowHistory(s => !s)}>
            {showHistory ? "Hide History" : "History"}
          </Btn>
          <Btn size="sm" variant="ghost" icon={<RefreshCw size={13}/>} onClick={() => entApi.refetch()}>Refresh</Btn>
        </div>
      </div>

      <Card padding={0}>
        <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", fontWeight: 600, fontSize: 13 }}>Modules</div>
        {modules.length === 0 && (
          <div style={{ padding: 16, fontSize: 13, color: "var(--text-secondary)" }}>No module entitlements assigned.</div>
        )}
        {modules.map(m => (
          <div key={m.id} data-testid={`module-row-${m.module_key}`} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 16px", borderBottom: "1px solid var(--border)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 13, fontWeight: 500 }}>{m.module_label}</span>
              <StatusBadge status={m.status}/>
            </div>
            {m.status === "ACTIVE" ? (
              <Btn size="sm" variant="ghost" icon={<XCircle size={13}/>}
                onClick={() => disableModule.execute(m.module_key).then(afterMutation)}>Disable</Btn>
            ) : (
              <Btn size="sm" variant="primary" icon={<CheckCircle2 size={13}/>}
                onClick={() => reenableModule.execute(m.module_key).then(afterMutation)}>Re-enable</Btn>
            )}
          </div>
        ))}
      </Card>

      <Card padding={0}>
        <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", fontWeight: 600, fontSize: 13 }}>Categories</div>
        {categories.length === 0 && (
          <div style={{ padding: 16, fontSize: 13, color: "var(--text-secondary)" }}>No category entitlements assigned.</div>
        )}
        {categories.map(c => (
          <div key={c.id} data-testid={`category-row-${c.category_id}`} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 16px", borderBottom: "1px solid var(--border)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 13, fontWeight: 500 }}>{c.category_label}</span>
              <StatusBadge status={c.status}/>
            </div>
            {c.status === "ACTIVE" ? (
              <Btn size="sm" variant="ghost" icon={<XCircle size={13}/>}
                onClick={() => disableCategory.execute(c.category_id).then(afterMutation)}>Disable</Btn>
            ) : (
              <Btn size="sm" variant="primary" icon={<CheckCircle2 size={13}/>}
                onClick={() => reenableCategory.execute(c.category_id).then(afterMutation)}>Re-enable</Btn>
            )}
          </div>
        ))}
      </Card>

      {showHistory && (
        <Card padding={0}>
          <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", fontWeight: 600, fontSize: 13 }}>Audit History</div>
          {(historyApi.data?.history ?? []).length === 0 && (
            <div style={{ padding: 16, fontSize: 13, color: "var(--text-secondary)" }}>No entitlement changes recorded yet.</div>
          )}
          {(historyApi.data?.history ?? []).map(h => (
            <div key={h.id} style={{ padding: "10px 16px", borderBottom: "1px solid var(--border)", fontSize: 12 }}>
              <div style={{ fontWeight: 600 }}>{h.event}</div>
              <div style={{ color: "var(--text-secondary)" }}>
                {h.previous_status ?? "—"} → {h.new_status ?? "—"} · by {h.actor_role ?? "system"} · {new Date(h.created_at).toLocaleString()}
                {h.reason ? ` · ${h.reason}` : ""}
              </div>
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}

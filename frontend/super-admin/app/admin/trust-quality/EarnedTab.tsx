"use client";
import { TableSurface } from "@serviceos/design-system";
/**
 * Badges held by a specific target — and the admin actions on them.
 *
 * This tab used to be a raw UUID paste box: the admin had to leave, find a
 * provider, copy its id, come back and paste it. It now searches providers by
 * name. It also exposes the two badge actions the backend has always had and the
 * console never called — manual award and revoke — which is what a "hybrid" or
 * "manual_award" badge rule is *for*: without them, every manual-award rule in
 * the system was unusable through the UI.
 */
import React, { useCallback, useState } from "react";
import { RefreshCw, Search, Users } from "lucide-react";
import {
  Card, Btn, Badge, Spinner, Select, Input, Modal, Textarea, Pagination, EmptyState,
} from "../../../components/shared/ui";
import {
  trustQualityApi, tenantApi, platformUsersApi, TQ_ENUMS,
  BadgeDefinition, EarnedBadge, EarnedBadgeDirectoryRow,
} from "../../../lib/api";
import { useAction, useApi } from "../../../hooks/useApi";

/** Target types that are tenants; everything else is looked up by id. */
const TENANT_TARGETS = ["tenant"];
const PAGE_SIZE = 25;

export function EarnedTab({ badges, BadgeIcon }: {
  badges: BadgeDefinition[];
  BadgeIcon: React.ComponentType<{ icon?: string | null; color?: string | null; size?: number }>;
}) {
  const [targetType, setTargetType] = useState("tenant");
  const [targetId, setTargetId] = useState("");
  const [targetLabel, setTargetLabel] = useState("");
  const [earned, setEarned] = useState<EarnedBadge[] | null>(null);
  const [awardOpen, setAwardOpen] = useState(false);
  const [revoking, setRevoking] = useState<EarnedBadge | null>(null);
  const [page, setPage] = useState(1);
  const [searchDraft, setSearchDraft] = useState("");
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [badgeFilter, setBadgeFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");

  const directory = useApi(
    useCallback(() => trustQualityApi.listBadgeAssignments({
      q: query || undefined,
      target_type: typeFilter || undefined,
      badge_key: badgeFilter || undefined,
      award_source: sourceFilter || undefined,
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
    }), [query, typeFilter, badgeFilter, sourceFilter, page]),
    [query, typeFilter, badgeFilter, sourceFilter, page],
  );
  const directoryRows = directory.data?.items ?? [];

  const load = useCallback(async (type: string, id: string) => {
    setEarned(await trustQualityApi.listEarnedBadges(type, id));
  }, []);

  const lookup = useAction(async () => {
    if (!targetId.trim()) return;
    await load(targetType, targetId.trim());
  });

  const refresh = useCallback(() => {
    if (targetId.trim()) load(targetType, targetId.trim());
  }, [load, targetType, targetId]);

  const inspectTarget = useCallback((row: EarnedBadgeDirectoryRow) => {
    setTargetType(row.target_type);
    setTargetId(row.target_id);
    setTargetLabel(row.target_name);
    void load(row.target_type, row.target_id);
  }, [load]);

  // Only badges defined for this target type can be awarded to it.
  const awardable = badges.filter((b): b is BadgeDefinition & { id: string } =>
    Boolean(b.id) && b.target_type === targetType && b.status === "active");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding={0}>
        <div style={{ padding: 16, borderBottom: "1px solid var(--border)" }}>
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16 }}>
            <div>
              <div style={{ fontSize: 15, fontWeight: 750 }}>Current badge holders</div>
              <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "4px 0 0" }}>
                Active, non-expired badges held by providers, staff members, and technicians.
              </p>
            </div>
            <Badge variant="info">{(directory.data?.total ?? 0).toLocaleString()} held</Badge>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "minmax(260px, 1.5fr) repeat(3, minmax(150px, 0.7fr)) auto", gap: 10, alignItems: "end", marginTop: 14 }}>
            <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
              <div style={{ flex: 1 }}>
                <Input label="Search holders" value={searchDraft} onChange={setSearchDraft}
                  icon={<Search size={14} />} placeholder="Name, email, phone, badge, or exact target ID" />
              </div>
              <Btn size="sm" onClick={() => { setQuery(searchDraft.trim()); setPage(1); }}>Search</Btn>
            </div>
            <Select label="Target type" value={typeFilter}
              onChange={value => { setTypeFilter(value); setPage(1); }}
              options={[{ value: "", label: "All target types" },
                ...TQ_ENUMS.badgeTargets.map(value => ({ value, label: value.replace(/_/g, " ") }))]} />
            <Select label="Badge" value={badgeFilter}
              onChange={value => { setBadgeFilter(value); setPage(1); }}
              options={[{ value: "", label: "All badges" },
                ...badges.filter(badge => badge.status === "active")
                  .map(badge => ({ value: badge.badge_key, label: badge.name }))]} />
            <Select label="Award source" value={sourceFilter}
              onChange={value => { setSourceFilter(value); setPage(1); }}
              options={[
                { value: "", label: "All sources" },
                { value: "auto_rule", label: "Automatic rule" },
                { value: "manual_admin", label: "Manual admin" },
                { value: "system_migration", label: "System migration" },
                { value: "seasonal_campaign", label: "Seasonal campaign" },
                { value: "appeal_approved", label: "Approved appeal" },
              ]} />
            <div style={{ display: "flex", gap: 6 }}>
              <Btn size="sm" variant="ghost" onClick={() => directory.refetch()}>
                <RefreshCw size={14} />
              </Btn>
              <Btn size="sm" variant="ghost" onClick={() => {
                setSearchDraft(""); setQuery(""); setTypeFilter("");
                setBadgeFilter(""); setSourceFilter(""); setPage(1);
              }}>Clear</Btn>
            </div>
          </div>
        </div>

        {directory.loading && directoryRows.length === 0 ? <Spinner /> : directory.error ? (
          <div style={{ padding: 20, color: "var(--danger-text)", fontSize: 13 }}>
            {directory.error} <Btn size="sm" variant="ghost" onClick={() => directory.refetch()}>Retry</Btn>
          </div>
        ) : directoryRows.length === 0 ? (
          <EmptyState icon={<Users />} title="No badge holders match"
            description="Clear filters or award a badge to an eligible provider or team member." />
        ) : (
          <>
            <div style={{ overflowX: "auto" }}>
              <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)", color: "var(--text-tertiary)" }}>
                    <th style={{ padding: "10px 16px" }}>Holder</th>
                    <th style={{ padding: "10px 16px" }}>Type</th>
                    <th style={{ padding: "10px 16px" }}>Badge</th>
                    <th style={{ padding: "10px 16px" }}>Visibility</th>
                    <th style={{ padding: "10px 16px" }}>Source</th>
                    <th style={{ padding: "10px 16px" }}>Earned</th>
                    <th style={{ padding: "10px 16px" }}>Expires</th>
                    <th style={{ padding: "10px 16px", textAlign: "right" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {directoryRows.map(row => (
                    <tr key={row.assignment_id} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "11px 16px", minWidth: 220 }}>
                        <div style={{ fontWeight: 650 }}>{row.target_name}</div>
                        <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                          {row.target_secondary || row.target_id}
                        </div>
                      </td>
                      <td style={{ padding: "11px 16px" }}>
                        <Badge variant="muted">{row.target_type}</Badge>
                      </td>
                      <td style={{ padding: "11px 16px", minWidth: 190 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <BadgeIcon icon={row.icon} color={row.color} size={16} />
                          <div>
                            <div style={{ fontWeight: 650 }}>{row.name}</div>
                            <div style={{ color: "var(--text-tertiary)", fontSize: 11 }}>Level {row.level ?? 1}</div>
                          </div>
                        </div>
                      </td>
                      <td style={{ padding: "11px 16px" }}>
                        <Badge variant={row.customer_visible ? "success" : "muted"}>
                          {row.customer_visible ? "Customer visible" : "Internal"}
                        </Badge>
                      </td>
                      <td style={{ padding: "11px 16px", color: "var(--text-secondary)" }}>
                        {row.award_source.replace(/_/g, " ")}
                      </td>
                      <td style={{ padding: "11px 16px", whiteSpace: "nowrap", color: "var(--text-secondary)" }}>
                        {row.earned_at ? row.earned_at.slice(0, 10) : "—"}
                      </td>
                      <td style={{ padding: "11px 16px", whiteSpace: "nowrap", color: "var(--text-secondary)" }}>
                        {row.expires_at ? row.expires_at.slice(0, 10) : "No expiry"}
                      </td>
                      <td style={{ padding: "11px 16px" }}>
                        <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                          <Btn size="sm" variant="ghost" onClick={() => inspectTarget(row)}>Manage</Btn>
                          <Btn size="sm" variant="ghost" onClick={() => setRevoking(row)}>Revoke</Btn>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </TableSurface>
            </div>
            <Pagination page={page} total={directory.data?.total ?? 0}
              pageSize={PAGE_SIZE} onPage={setPage} alwaysShow />
          </>
        )}
      </Card>

      <Card>
        <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>Badges held by a target</div>
        <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 12px" }}>
          Look up the fixed badges a provider, staff member or technician currently holds,
          then award or revoke one by hand.
        </p>
        <div style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" }}>
          <div style={{ minWidth: 180 }}>
            <Select label="Target type" value={targetType}
              onChange={v => { setTargetType(v); setTargetId(""); setTargetLabel(""); setEarned(null); }}
              options={TQ_ENUMS.badgeTargets.map(v => ({ value: v, label: v.replace(/_/g, " ") }))} />
          </div>
          <div style={{ flex: 1, minWidth: 300 }}>
            {TENANT_TARGETS.includes(targetType) ? (
              <TenantPicker value={targetId} label={targetLabel}
                onPick={(id, name) => { setTargetId(id); setTargetLabel(name); setEarned(null); }} />
            ) : (
              <StaffPicker value={targetId} label={targetLabel}
                targetType={targetType}
                onPick={(id, name) => { setTargetId(id); setTargetLabel(name); setEarned(null); }} />
            )}
          </div>
          <Btn disabled={!targetId.trim() || lookup.loading} onClick={() => lookup.execute()}>
            {lookup.loading ? "Loading…" : "Look up"}
          </Btn>
        </div>
        {lookup.error && (
          <p style={{ fontSize: 12, color: "var(--danger-text)", margin: "10px 0 0" }}>{lookup.error}</p>
        )}
      </Card>

      {earned !== null && (
        <Card>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <div style={{ fontSize: 14, fontWeight: 700 }}>
              {targetLabel || "Target"} · {earned.length} badge{earned.length === 1 ? "" : "s"}
            </div>
            <Btn size="sm" disabled={awardable.length === 0} onClick={() => setAwardOpen(true)}>
              Award a badge
            </Btn>
          </div>
          {awardable.length === 0 && (
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "0 0 12px" }}>
              No active badge is defined for target type “{targetType.replace(/_/g, " ")}”, so none can be awarded.
            </p>
          )}
          {earned.length === 0 ? (
            <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>This target holds no badges.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {earned.map(b => (
                <div key={b.assignment_id} style={{ display: "flex", alignItems: "center", gap: 12,
                  padding: "10px 12px", border: "1px solid var(--border)",
                  borderRadius: "var(--radius-md)", background: "var(--surface)" }}>
                  <BadgeIcon icon={b.icon} color={b.color} size={16} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, fontSize: 13 }}>{b.name}</div>
                    <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                      {b.award_source.replace(/_/g, " ")}
                      {b.earned_at && ` · earned ${b.earned_at.slice(0, 10)}`}
                      {b.expires_at && ` · expires ${b.expires_at.slice(0, 10)}`}
                    </div>
                  </div>
                  {!b.customer_visible && <Badge variant="muted" size="sm">internal</Badge>}
                  <Btn size="sm" variant="ghost" onClick={() => setRevoking(b)}>Revoke</Btn>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      <AwardModal open={awardOpen} onClose={() => setAwardOpen(false)} badges={awardable}
        targetType={targetType} targetId={targetId}
        onDone={() => { setAwardOpen(false); refresh(); directory.refetch(); }} />
      <RevokeModal badge={revoking} onClose={() => setRevoking(null)}
        onDone={() => { setRevoking(null); refresh(); directory.refetch(); }} />
    </div>
  );
}

/** Search the canonical staff directory for staff and technician badge targets. */
function StaffPicker({ value, label, targetType, onPick }: {
  value: string; label: string; targetType: string;
  onPick: (id: string, name: string) => void;
}) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<{ id: string; name: string; tenant: string | null }[] | null>(null);

  const search = useAction(async () => {
    const page = await platformUsersApi.list({
      role: "staff", q: q.trim() || undefined, page: 1, limit: 10,
    });
    setResults((page.users ?? []).map(user => ({
      id: user.id,
      name: user.full_name || user.email,
      tenant: user.tenant_id,
    })));
  });

  return (
    <div>
      <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
        <div style={{ flex: 1 }}>
          <Input label={targetType === "technician" ? "Technician" : "Staff member"}
            value={q} onChange={setQ} icon={<Search size={14} />}
            hint={value ? `Selected: ${label} (${value.slice(0, 8)})` : "Search the staff directory by name, email or phone."}
            placeholder="Search staff directory" />
        </div>
        <Btn size="sm" variant="secondary" disabled={search.loading} onClick={() => search.execute()}>
          {search.loading ? "..." : "Search"}
        </Btn>
      </div>
      {search.error && <p style={{ margin: "8px 0 0", fontSize: 12, color: "var(--danger-text)" }}>{search.error}</p>}
      {results !== null && (
        <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 6 }}>
          {results.length === 0
            ? <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>No active staff matched.</span>
            : results.map(result => (
              <Btn key={result.id} size="sm" variant={result.id === value ? "primary" : "ghost"}
                onClick={() => { onPick(result.id, result.name); setResults(null); }}>
                {result.name}{result.tenant ? ` · ${result.tenant.slice(0, 8)}` : ""}
              </Btn>
            ))}
        </div>
      )}
    </div>
  );
}

/** Search providers by name so the admin never has to hunt for a UUID. */
function TenantPicker({ value, label, onPick }: {
  value: string; label: string; onPick: (id: string, name: string) => void;
}) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<{ id: string; name: string }[] | null>(null);

  const search = useAction(async () => {
    if (q.trim().length < 2) { setResults([]); return; }
    const page = await tenantApi.list({ search: q.trim(), limit: 10 });
    setResults((page.tenants ?? []).map(t => ({
      id: t.tenant_id, name: t.tenant_name || t.tenant_id.slice(0, 8),
    })));
  });

  return (
    <div>
      <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
        <div style={{ flex: 1 }}>
          <Input label="Provider" value={q} onChange={setQ}
            icon={<Search size={14} />}
            hint={value ? `Selected: ${label} (${value.slice(0, 8)})` : "Type at least 2 characters, then Search."}
            placeholder="Search providers by name" />
        </div>
        <Btn size="sm" variant="secondary" disabled={search.loading} onClick={() => search.execute()}>
          {search.loading ? "…" : "Search"}
        </Btn>
      </div>
      {results !== null && (
        <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 6 }}>
          {results.length === 0
            ? <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>No providers matched.</span>
            : results.map(r => (
              <Btn key={r.id} size="sm" variant={r.id === value ? "primary" : "ghost"}
                onClick={() => { onPick(r.id, r.name); setResults(null); }}>
                {r.name}
              </Btn>
            ))}
        </div>
      )}
    </div>
  );
}

function AwardModal({ open, onClose, onDone, badges, targetType, targetId }: {
  open: boolean; onClose: () => void; onDone: () => void;
  badges: BadgeDefinition[]; targetType: string; targetId: string;
}) {
  const [badgeId, setBadgeId] = useState("");
  const [reason, setReason] = useState("");

  React.useEffect(() => {
    if (open) { setBadgeId(badges[0]?.id ?? ""); setReason(""); }
  }, [open, badges]);

  const award = useAction(async () => {
    await trustQualityApi.manualAwardBadge({
      badge_id: badgeId, target_type: targetType, target_id: targetId, reason: reason.trim() });
    onDone();
  });

  if (!open) return null;
  return (
    <Modal open onClose={onClose} title="Award a badge" size="sm">
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <Select label="Badge" value={badgeId} onChange={setBadgeId}
          options={badges.map(b => ({ value: b.id, label: b.name }))} />
        <Textarea label="Reason" value={reason} onChange={setReason} rows={3} required
          placeholder="Why is this badge being awarded by hand?" />
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
          Manual awards are recorded in the audit trail with your account. A later
          recalculation will not remove a manually awarded badge unless a removal
          criterion matches.
        </p>
        {award.error && <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{award.error}</p>}
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <Btn variant="ghost" onClick={onClose}>Cancel</Btn>
          <Btn disabled={!badgeId || !reason.trim() || award.loading} onClick={() => award.execute()}>
            {award.loading ? "Awarding…" : "Award badge"}
          </Btn>
        </div>
      </div>
    </Modal>
  );
}

function RevokeModal({ badge, onClose, onDone }: {
  badge: EarnedBadge | null; onClose: () => void; onDone: () => void;
}) {
  const [reason, setReason] = useState("");
  React.useEffect(() => { if (badge) setReason(""); }, [badge]);

  const revoke = useAction(async () => {
    if (!badge) return;
    await trustQualityApi.revokeBadge(badge.assignment_id, reason.trim());
    onDone();
  });

  if (!badge) return null;
  return (
    <Modal open onClose={onClose} title={`Revoke “${badge.name}”`} size="sm">
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>
          {badge.customer_visible
            ? "This badge is visible to customers — revoking it changes what they see immediately."
            : "This badge is internal and not shown to customers."}
        </p>
        <Textarea label="Reason" value={reason} onChange={setReason} rows={3} required
          placeholder="Why is this badge being revoked?" />
        {revoke.error && <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{revoke.error}</p>}
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <Btn variant="ghost" onClick={onClose}>Cancel</Btn>
          <Btn variant="danger" disabled={!reason.trim() || revoke.loading} onClick={() => revoke.execute()}>
            {revoke.loading ? "Revoking…" : "Revoke badge"}
          </Btn>
        </div>
      </div>
    </Modal>
  );
}

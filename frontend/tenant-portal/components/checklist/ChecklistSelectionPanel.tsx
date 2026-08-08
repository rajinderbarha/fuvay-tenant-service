"use client";
/**
 * Checklist selection — this provider chooses which of the ADMIN's authored
 * checklist points its technicians must complete for one service.
 *
 * Division of responsibility (product rule):
 *   ADMIN  authors the library (templates -> sections -> points).
 *   TENANT selects at least `minimum_required` of them, per service.
 *
 * The minimum, the selectable list and whether the requirement is met all come
 * from the backend (`readiness`). Nothing here recomputes the rule, so the UI
 * can never disagree with what the server will actually enforce -- the Save
 * button is disabled below the minimum purely as a courtesy, and a server
 * rejection is still surfaced verbatim if it happens anyway.
 *
 * Two states are deliberately distinguished, because telling a provider to
 * "pick 5" from an empty list would be nonsense:
 *   nothing_authored -> the admin has published no checklist for this service.
 *   cannot_satisfy   -> fewer points exist than the minimum requires.
 * Both are admin gaps, and both say so rather than blaming the provider.
 */
import React, { useCallback, useMemo, useState } from "react";
import { Card, Badge, Btn, Skeleton, EmptyState } from "../shared/ui";
import { checklistSelectionApi } from "../../lib/api";
import type { SelectableChecklistItem } from "../../lib/api";
import { useApi, useAction } from "../../hooks/useApi";

interface Props {
  masterServiceId: string;
  serviceName: string;
}

export function ChecklistSelectionPanel({ masterServiceId, serviceName }: Props) {
  const selectable = useApi(
    useCallback(() => checklistSelectionApi.listSelectable(masterServiceId), [masterServiceId]),
    [masterServiceId],
  );

  // Local draft of the selection, seeded from the server's saved state once it
  // arrives. Kept separate so the user can tick around freely before saving.
  const [draft, setDraft] = useState<Set<string> | null>(null);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  const readiness = selectable.data?.readiness ?? null;
  const items = selectable.data?.items ?? [];
  const minimum = readiness?.minimum_required ?? 5;

  const selected = useMemo(
    () => draft ?? new Set(readiness?.selected_item_ids ?? []),
    [draft, readiness],
  );

  const save = useAction(
    (ids: string[]) => checklistSelectionApi.setSelection(masterServiceId, ids),
    {
      onSuccess: () => {
        setSavedMessage("Checklist points saved for this service.");
        setDraft(null);          // fall back to server truth
        selectable.refetch();
      },
    },
  );

  function toggle(id: string) {
    setSavedMessage(null);
    const next = new Set(selected);
    if (next.has(id)) next.delete(id); else next.add(id);
    setDraft(next);
  }

  if (selectable.loading) {
    return <Card><Skeleton /><Skeleton /><Skeleton /></Card>;
  }
  if (selectable.error) {
    return (
      <Card>
        <p style={{ fontSize: 13, color: "var(--danger)", margin: 0 }}>{selectable.error}</p>
        <div style={{ marginTop: 12 }}>
          <Btn variant="secondary" onClick={selectable.refetch}>Try again</Btn>
        </div>
      </Card>
    );
  }

  // Admin gaps: say what is actually wrong instead of asking for the impossible.
  if (readiness?.nothing_authored) {
    return (
      <Card>
        <EmptyState
          title="No checklist published for this service yet"
          description={
            `The platform team has not published any checklist points for ${serviceName}. ` +
            `Once they do, you will choose at least ${minimum} of them here for your technicians.`
          }
        />
      </Card>
    );
  }
  if (readiness?.cannot_satisfy) {
    return (
      <Card>
        <EmptyState
          title="Not enough checklist points published"
          description={
            `${serviceName} requires at least ${minimum} checklist points, but only ` +
            `${readiness.selectable_total} have been published. Please ask the platform team ` +
            `to publish more before setting this up.`
          }
        />
      </Card>
    );
  }

  const count = selected.size;
  const shortfall = Math.max(0, minimum - count);
  const meetsMinimum = count >= minimum;
  const dirty = draft !== null;

  // Group by the admin's own sections so the provider reads the checklist the
  // way it was authored, rather than as one flat list.
  const grouped = new Map<string, SelectableChecklistItem[]>();
  for (const item of items) {
    const key = item.section_title || item.template_name || "Checklist";
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key)!.push(item);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
          <div>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
              Checklist points for {serviceName}
            </h3>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
              Choose at least {minimum} points your technicians must complete on every
              {" "}{serviceName} job. These come from the platform&apos;s authored checklist.
            </p>
          </div>
          <Badge variant={meetsMinimum ? "success" : "warning"}>
            {count} of {minimum} selected
          </Badge>
        </div>

        {!meetsMinimum ? (
          <p style={{ fontSize: 13, color: "var(--warning)", margin: "12px 0 0" }}>
            Select {shortfall} more {shortfall === 1 ? "point" : "points"} to meet the minimum.
          </p>
        ) : null}

        {savedMessage ? (
          <p style={{ fontSize: 13, color: "var(--success)", margin: "12px 0 0" }}>{savedMessage}</p>
        ) : null}
        {save.error ? (
          <p style={{ fontSize: 13, color: "var(--danger)", margin: "12px 0 0" }}>
            {save.error}
            {save.requestId ? <span style={{ opacity: 0.7 }}> (ref {save.requestId})</span> : null}
          </p>
        ) : null}

        <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
          <Btn
            onClick={() => save.execute(Array.from(selected))}
            disabled={!meetsMinimum || save.loading || !dirty}
          >
            {save.loading ? "Saving…" : "Save selection"}
          </Btn>
          {dirty ? (
            <Btn variant="secondary" onClick={() => { setDraft(null); setSavedMessage(null); }}>
              Discard changes
            </Btn>
          ) : null}
        </div>
      </Card>

      {Array.from(grouped.entries()).map(([section, sectionItems]) => (
        <Card key={section}>
          <h4 style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px" }}>
            {section}
          </h4>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {sectionItems.map(item => {
              const isOn = selected.has(item.id);
              return (
                <label
                  key={item.id}
                  style={{
                    display: "flex", alignItems: "flex-start", gap: 10, cursor: "pointer",
                    padding: 12, borderRadius: 8,
                    border: `1px solid ${isOn ? "var(--accent)" : "var(--border)"}`,
                    background: isOn ? "var(--accent-soft, rgba(56,104,224,0.06))" : "transparent",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={isOn}
                    onChange={() => toggle(item.id)}
                    aria-label={item.label}
                    style={{ marginTop: 2, cursor: "pointer" }}
                  />
                  <span style={{ flex: 1, minWidth: 0 }}>
                    <span style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                      {item.label}
                    </span>
                    {item.help_text ? (
                      <span style={{ display: "block", fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>
                        {item.help_text}
                      </span>
                    ) : null}
                    <span style={{ display: "flex", gap: 6, marginTop: 6, flexWrap: "wrap" }}>
                      {item.evidence_required ? <Badge variant="info">Photo required</Badge> : null}
                      {item.phase ? <Badge variant="muted">{item.phase}</Badge> : null}
                    </span>
                  </span>
                </label>
              );
            })}
          </div>
        </Card>
      ))}
    </div>
  );
}

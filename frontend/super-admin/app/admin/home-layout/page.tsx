"use client";
/**
 * Home Layout — the order and visibility of every section on the customer Home
 * screen.
 *
 * Real gap this closes: the layout was fixed in the mobile app, so re-ordering
 * Home or hiding a section meant an app release. The backend now holds it
 * (home_section_settings, migration 236/237) and the app draws whatever this page
 * says -- but until now the only way to change it was a raw API call.
 *
 * Two deliberate constraints, both surfaced rather than hidden:
 *
 *  - The key list is CLOSED. Each key maps to a renderer the app ships, so a
 *    section can be moved, renamed or switched off but not invented; a made-up
 *    key would be a row that does nothing on every device.
 *  - Order is saved as a whole list, because that is how the server validates it
 *    -- every key checked before any is written, so a bad list cannot leave the
 *    screen half-reordered.
 */
import React, { useCallback, useMemo, useState } from "react";
import { useApi, useAction } from "../../../hooks/useApi";
import { homeSectionApi, type HomeSectionSetting } from "../../../lib/api";
import {
  Card, Badge, Btn, Input, Skeleton, SectionHeader,
} from "../../../components/shared/ui";

/** What each section is, in the operator's terms. Kept here rather than derived
 * from the key so the page reads as a description of the customer's screen
 * instead of a list of identifiers. */
const SECTION_INFO: Record<string, { label: string; blurb: string }> = {
  active_booking: {
    label: "My Booking",
    blurb: "The customer's live job — provider, rating, badges and the booked slot.",
  },
  quick_problems: {
    label: "Problem grid",
    blurb: "Named problems booked in one tap, e.g. AC Not Cooling. The shortest route to a booking.",
  },
  campaign_top: { label: "Banner slot — top", blurb: "Above the services. Several banners here become a carousel." },
  campaign_after_problems: { label: "Banner slot — under problems", blurb: "Directly beneath the problem grid." },
  service_grid: { label: "Services Nearby", blurb: "The categories bookable at the customer's PIN code." },
  campaign_after_services: { label: "Banner slot — under services", blurb: "Beneath the service grid." },
  assistant_entry: { label: "Assistant card", blurb: "“Not sure what to book?” — the way in for someone who cannot name the problem." },
  campaign_mid: { label: "Banner slot — middle", blurb: "Below the assistant card." },
  global_services: { label: "Build with Fuvay", blurb: "Project work — web, app, software. Creates a callback lead, not a booking." },
  how_it_works: { label: "How it works", blurb: "Three steps explaining the flow. Aimed at first-time customers." },
  trust_benefits: { label: "What you're promised", blurb: "Verification, cost approval and call privacy, each with its substantiation." },
  campaign_bottom: { label: "Banner slot — bottom", blurb: "End of the screen." },
};

function info(key: string) {
  return SECTION_INFO[key] ?? {
    label: key,
    // A key with no entry here means the backend knows a section this page has
    // not been told about yet -- said plainly rather than shown as a bare slug
    // with no explanation.
    blurb: "Added by a newer backend than this page. It still re-orders and toggles normally.",
  };
}

export default function HomeLayoutPage() {
  const { data, loading, error, refetch } = useApi(
    useCallback(() => homeSectionApi.list(), []),
    [],
  );

  /** Local working order. Null until loaded, and reset by every refetch, so the
   * page never shows a pending order as if it were saved. */
  const [order, setOrder] = useState<HomeSectionSetting[] | null>(null);
  const [renaming, setRenaming] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const sections = useMemo(() => {
    if (order) return order;
    return [...(data?.items ?? [])].sort((a, b) => a.display_order - b.display_order);
  }, [order, data]);

  const dirty = order !== null;
  const enabledCount = sections.filter(s => s.is_enabled).length;

  function move(index: number, delta: number) {
    const next = [...sections];
    const target = index + delta;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    setOrder(next);
  }

  const saveOrder = useAction(useCallback(async () => {
    if (!order) return;
    await homeSectionApi.reorder(order.map(s => s.section_key));
    setOrder(null);
    refetch();
  }, [order, refetch]));

  const toggle = useAction(useCallback(async (section: HomeSectionSetting) => {
    await homeSectionApi.update(section.section_key, { is_enabled: !section.is_enabled });
    setOrder(null);
    refetch();
  }, [refetch]));

  const saveRename = useAction(useCallback(async (key: string) => {
    // Empty clears the override, which returns the section to the wording the
    // app ships -- distinct from setting it to an empty heading.
    await homeSectionApi.update(key, { title_override: renameValue.trim() || null });
    setRenaming(null);
    setRenameValue("");
    setOrder(null);
    refetch();
  }, [renameValue, refetch]));

  return (
    <div style={{ padding: 24, maxWidth: 900 }}>
      <SectionHeader
        title="Home Layout"
        subtitle={`Order and visibility of the customer Home screen — ${enabledCount} of ${sections.length} sections on`}
        actions={
          dirty ? (
            <div style={{ display: "flex", gap: 8 }}>
              <Btn variant="ghost" onClick={() => setOrder(null)}>Discard</Btn>
              <Btn onClick={() => saveOrder.execute()} disabled={saveOrder.loading}>
                {saveOrder.loading ? "Saving…" : "Save order"}
              </Btn>
            </div>
          ) : undefined
        }
      />

      {loading && (
        <Card style={{ marginTop: 16 }}>
          <Skeleton height={28} /><Skeleton height={28} style={{ marginTop: 10 }} />
        </Card>
      )}

      {error && (
        <Card style={{ marginTop: 16 }}>
          <p style={{ color: "var(--danger-text)", fontSize: 13, margin: 0 }}>{error}</p>
        </Card>
      )}

      {(saveOrder.error || toggle.error || saveRename.error) && (
        <Card style={{ marginTop: 16 }}>
          <p style={{ color: "var(--danger-text)", fontSize: 13, margin: 0 }}>
            {saveOrder.error || toggle.error || saveRename.error}
          </p>
        </Card>
      )}

      {!loading && !error && (
        <>
          <p style={{ fontSize: 12.5, color: "var(--text-tertiary)", marginTop: 16 }}>
            Top of this list is the top of the customer&apos;s screen. A section with nothing to
            show — an empty banner slot, or no live booking — draws nothing and takes no space,
            so leaving it on costs the customer nothing.
          </p>

          <Card style={{ marginTop: 12 }} padding={0}>
            {sections.map((section, index) => {
              const meta = info(section.section_key);
              return (
                <div
                  key={section.section_key}
                  style={{
                    display: "flex", alignItems: "flex-start", gap: 12,
                    padding: "12px 14px",
                    borderTop: index === 0 ? "none" : "1px solid var(--border)",
                    opacity: section.is_enabled ? 1 : 0.55,
                  }}
                >
                  <div style={{ display: "flex", flexDirection: "column", gap: 2, flexShrink: 0 }}>
                    <Btn
                      variant="ghost" size="sm"
                      onClick={() => move(index, -1)}
                      disabled={index === 0}
                      aria-label={`Move ${meta.label} up`}
                    >
                      ↑
                    </Btn>
                    <Btn
                      variant="ghost" size="sm"
                      onClick={() => move(index, 1)}
                      disabled={index === sections.length - 1}
                      aria-label={`Move ${meta.label} down`}
                    >
                      ↓
                    </Btn>
                  </div>

                  <div style={{ width: 22, flexShrink: 0, textAlign: "right", color: "var(--text-tertiary)", fontSize: 12, paddingTop: 8 }}>
                    {index + 1}
                  </div>

                  <div style={{ flex: 1, minWidth: 0, paddingTop: 4 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                        {section.title_override || meta.label}
                      </span>
                      {section.title_override ? <Badge variant="info" size="sm">Renamed</Badge> : null}
                      {!section.is_enabled ? <Badge variant="muted" size="sm">Off</Badge> : null}
                      <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{section.section_key}</span>
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>{meta.blurb}</div>

                    {renaming === section.section_key ? (
                      <div style={{ display: "flex", alignItems: "flex-end", gap: 8, marginTop: 8 }}>
                        <div style={{ flex: 1 }}>
                          <Input
                            label="Heading shown to customers"
                            value={renameValue}
                            placeholder={meta.label}
                            hint="Leave empty to use the app's own wording."
                            onChange={setRenameValue}
                          />
                        </div>
                        <Btn size="sm" onClick={() => saveRename.execute(section.section_key)} disabled={saveRename.loading}>
                          Save
                        </Btn>
                        <Btn size="sm" variant="ghost" onClick={() => { setRenaming(null); setRenameValue(""); }}>
                          Cancel
                        </Btn>
                      </div>
                    ) : null}
                  </div>

                  <div style={{ display: "flex", gap: 6, flexShrink: 0, paddingTop: 4 }}>
                    <Btn
                      variant="ghost" size="sm"
                      onClick={() => {
                        setRenaming(section.section_key);
                        setRenameValue(section.title_override ?? "");
                      }}
                    >
                      Rename
                    </Btn>
                    <Btn variant="ghost" size="sm" onClick={() => toggle.execute(section)} disabled={toggle.loading}>
                      {section.is_enabled ? "Turn off" : "Turn on"}
                    </Btn>
                  </div>
                </div>
              );
            })}
          </Card>

          {dirty ? (
            <p style={{ fontSize: 12.5, color: "var(--warning-text)", marginTop: 12 }}>
              This order has not been saved yet — customers still see the previous one.
            </p>
          ) : null}
        </>
      )}
    </div>
  );
}

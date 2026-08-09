"use client";
/**
 * Home Banners — the admin surface for the promotional carousel on the
 * customer Home screen.
 *
 * Real gap this closes: the customer_campaigns engine already powered that
 * carousel, but BOTH of its routers were written and never mounted, so
 * there was no way for anyone to create, schedule or edit a banner. The
 * carousel still rendered (customer_home calls the service in-process),
 * which is exactly why the gap went unnoticed — the feature looked alive
 * from the customer side while being unmanageable from this one.
 *
 * "Enabled" and "live" are shown as different things on purpose: the toggle
 * is the operator's switch, while the schedule window decides whether
 * customers can see it right now. Conflating them is how a campaign goes out
 * early, so the status column says which one is holding a banner back.
 */
import React, { useCallback, useMemo, useState } from "react";
import { useApi, useAction } from "../../../hooks/useApi";
import {
  customerCampaignApi,
  CAMPAIGN_DEEPLINK_PREFIXES,
  CAMPAIGN_STYLES,
  CAMPAIGN_PLACEMENTS,
  type CustomerCampaign,
  type CustomerCampaignPayload,
} from "../../../lib/api";
import {
  Card, Badge, Btn, Input, Select, Modal, Spinner, Skeleton, SectionHeader, RowActions,
} from "../../../components/shared/ui";
import { IconPicker } from "../../../components/shared/IconPicker";
import DeeplinkPicker from "./DeeplinkPicker";

type FormState = {
  internal_name: string;
  eyebrow: string;
  title: string;
  description: string;
  artwork_url_light: string;
  artwork_url_dark: string;
  cta_label: string;
  cta_deeplink: string;
  display_style: string;
  placement: string;
  accent_color: string;
  badge_text: string;
  priority: string;
  starts_at: string;
  ends_at: string;
  target_zipcodes: string;
};

const EMPTY_FORM: FormState = {
  internal_name: "", eyebrow: "", title: "", description: "",
  artwork_url_light: "", artwork_url_dark: "",
  cta_label: "", cta_deeplink: "",
  display_style: "hero", placement: "campaign_top",
  accent_color: "", badge_text: "",
  priority: "100", starts_at: "", ends_at: "", target_zipcodes: "",
};

/** Labels for the table, keyed off the same lists the form offers so the two
 * cannot describe a banner differently. */
const STYLE_LABEL: Record<string, string> = {
  hero: "Hero", festival: "Festival", strip: "Strip",
};
const SLOT_LABEL: Record<string, string> = {
  campaign_top: "Top",
  campaign_after_problems: "Under problems",
  campaign_after_services: "Under services",
  campaign_mid: "Middle",
  campaign_bottom: "Bottom",
};

/** #rgb or #rrggbb. Checked before saving because the customer app derives the
 * label colour from this value, and an unparseable one would silently fall back
 * to white text -- which is unreadable on a light accent. */
const HEX = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i;

/** `datetime-local` needs `YYYY-MM-DDTHH:mm`; the API speaks ISO-8601. */
function isoToLocalInput(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function localInputToIso(value: string): string | null {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
}

function formFrom(c: CustomerCampaign): FormState {
  return {
    internal_name: c.internal_name,
    eyebrow: c.eyebrow ?? "",
    title: c.title,
    description: c.description ?? "",
    artwork_url_light: c.artwork_url_light ?? "",
    artwork_url_dark: c.artwork_url_dark ?? "",
    cta_label: c.cta_label ?? "",
    cta_deeplink: c.cta_deeplink ?? "",
    display_style: c.display_style || "hero",
    placement: c.placement || "campaign_top",
    accent_color: c.accent_color ?? "",
    badge_text: c.badge_text ?? "",
    priority: String(c.priority),
    starts_at: isoToLocalInput(c.starts_at),
    ends_at: isoToLocalInput(c.ends_at),
    target_zipcodes: (c.target_zipcodes ?? []).join(", "),
  };
}

/** Mirrors the server's own window check — the server stays authoritative,
 * this only explains its decision to the operator. */
function visibility(c: CustomerCampaign): { label: string; variant: "success" | "warning" | "muted" } {
  if (!c.is_enabled) return { label: "Off", variant: "muted" };
  const now = Date.now();
  if (c.starts_at && new Date(c.starts_at).getTime() > now) return { label: "Scheduled", variant: "warning" };
  if (c.ends_at && new Date(c.ends_at).getTime() <= now) return { label: "Ended", variant: "muted" };
  return { label: "Live", variant: "success" };
}

function parseList(value: string): string[] {
  return value.split(",").map(v => v.trim()).filter(Boolean);
}

export default function HomeBannersPage() {
  const { data, loading, error, refetch } = useApi(
    useCallback(() => customerCampaignApi.list(), []),
    [],
  );

  const [editing, setEditing] = useState<CustomerCampaign | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [formError, setFormError] = useState<string | null>(null);

  const campaigns = useMemo(() => data?.items ?? [], [data]);
  const liveCount = useMemo(
    () => campaigns.filter(c => visibility(c).label === "Live").length,
    [campaigns],
  );
  /** How many LIVE banners share each slot. Several in one slot become a
   * carousel on Home, which is worth showing here: it is the difference between
   * a banner customers see and one they have to swipe to. */
  const slotCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const c of campaigns) {
      if (visibility(c).label !== "Live") continue;
      counts[c.placement] = (counts[c.placement] ?? 0) + 1;
    }
    return counts;
  }, [campaigns]);

  const closeModal = useCallback(() => {
    setEditing(null); setCreating(false); setForm(EMPTY_FORM); setFormError(null);
  }, []);

  const buildPayload = useCallback((): CustomerCampaignPayload | null => {
    if (!form.internal_name.trim()) { setFormError("Internal name is required."); return null; }
    if (!form.title.trim()) { setFormError("Title is required."); return null; }

    const deeplink = form.cta_deeplink.trim();
    if (form.cta_label.trim() && !deeplink) {
      setFormError("A button label needs a destination, or the button does nothing.");
      return null;
    }
    // Checked here as well as server-side so the operator sees the rule
    // before a round-trip: only known in-app destinations are accepted,
    // never an arbitrary external URL.
    if (deeplink && !CAMPAIGN_DEEPLINK_PREFIXES.some(p => deeplink.startsWith(p))) {
      setFormError(`Destination must start with one of: ${CAMPAIGN_DEEPLINK_PREFIXES.join(", ")}`);
      return null;
    }

    const accent = form.accent_color.trim();
    if (accent && !HEX.test(accent)) {
      setFormError("Accent colour must be a hex value such as #f59e0b.");
      return null;
    }
    // Stated rather than silently ignored: a badge on a hero card would be
    // saved and never drawn, which looks like the field is broken.
    if (form.badge_text.trim() && form.display_style !== "festival") {
      setFormError("A badge only appears on the Festival style. Switch the style, or clear the badge.");
      return null;
    }

    const startsAt = localInputToIso(form.starts_at);
    const endsAt = localInputToIso(form.ends_at);
    if (startsAt && endsAt && new Date(startsAt) > new Date(endsAt)) {
      setFormError("The start date must be before the end date.");
      return null;
    }

    setFormError(null);
    return {
      internal_name: form.internal_name.trim(),
      eyebrow: form.eyebrow.trim() || null,
      title: form.title.trim(),
      description: form.description.trim() || null,
      artwork_url_light: form.artwork_url_light.trim() || null,
      artwork_url_dark: form.artwork_url_dark.trim() || null,
      cta_label: form.cta_label.trim() || null,
      cta_deeplink: deeplink || null,
      display_style: form.display_style,
      placement: form.placement,
      accent_color: accent || null,
      badge_text: form.badge_text.trim() || null,
      priority: Number(form.priority) || 100,
      starts_at: startsAt,
      ends_at: endsAt,
      target_zipcodes: parseList(form.target_zipcodes),
    };
  }, [form]);

  const save = useAction(useCallback(async () => {
    const payload = buildPayload();
    if (!payload) return;
    if (editing) await customerCampaignApi.update(editing.campaign_id, payload);
    else await customerCampaignApi.create({ ...payload, is_enabled: true });
    closeModal();
    refetch();
  }, [buildPayload, editing, closeModal, refetch]));

  const toggle = useAction(useCallback(async (c: CustomerCampaign) => {
    await customerCampaignApi.update(c.campaign_id, { is_enabled: !c.is_enabled });
    refetch();
  }, [refetch]));

  const remove = useAction(useCallback(async (c: CustomerCampaign) => {
    if (!window.confirm(`Delete "${c.internal_name}"? This cannot be undone.`)) return;
    await customerCampaignApi.remove(c.campaign_id);
    refetch();
  }, [refetch]));

  return (
    <div style={{ padding: 24, maxWidth: 1150 }}>
      <SectionHeader
        title="Home Banners"
        subtitle={`Promotional carousel on the customer Home screen — ${liveCount} live right now`}
        actions={
          <Btn onClick={() => { setCreating(true); setEditing(null); setForm(EMPTY_FORM); }}>
            New banner
          </Btn>
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

      {!loading && !error && campaigns.length === 0 && (
        <Card style={{ marginTop: 16 }}>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>
            No banners yet. Create one to start promoting on the customer Home screen.
          </p>
        </Card>
      )}

      {!loading && campaigns.length > 0 && (
        <Card style={{ marginTop: 16 }} padding={0}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ textAlign: "left", color: "var(--text-tertiary)", fontSize: 11.5 }}>
                  <th style={{ padding: "10px 14px" }}>Priority</th>
                  <th style={{ padding: "10px 14px" }}>Banner</th>
                  <th style={{ padding: "10px 14px" }}>Style &amp; slot</th>
                  <th style={{ padding: "10px 14px" }}>Button</th>
                  <th style={{ padding: "10px 14px" }}>Targeting</th>
                  <th style={{ padding: "10px 14px" }}>Schedule</th>
                  <th style={{ padding: "10px 14px" }}>Status</th>
                  <th style={{ padding: "10px 14px" }} />
                </tr>
              </thead>
              <tbody>
                {campaigns.map(c => {
                  const v = visibility(c);
                  return (
                    <tr key={c.campaign_id} style={{ borderTop: "1px solid var(--border)" }}>
                      <td style={{ padding: "12px 14px", color: "var(--text-tertiary)" }}>{c.priority}</td>
                      <td style={{ padding: "12px 14px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                          {c.artwork_url_light ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              src={c.artwork_url_light}
                              alt=""
                              style={{ width: 64, height: 36, objectFit: "cover", borderRadius: 6,
                                background: "var(--surface-sunken)", flexShrink: 0 }}
                            />
                          ) : (
                            <div style={{ width: 64, height: 36, borderRadius: 6, flexShrink: 0,
                              background: "var(--surface-sunken)" }} />
                          )}
                          <div style={{ minWidth: 0 }}>
                            <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>{c.title}</div>
                            <div style={{ fontSize: 11.5, color: "var(--text-tertiary)" }}>{c.internal_name}</div>
                          </div>
                        </div>
                      </td>
                      <td style={{ padding: "12px 14px", fontSize: 12 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          {c.accent_color ? (
                            <span
                              title={c.accent_color}
                              style={{ width: 12, height: 12, borderRadius: 3, flexShrink: 0,
                                background: c.accent_color, border: "1px solid var(--border)" }}
                            />
                          ) : null}
                          <span style={{ color: "var(--text-primary)" }}>
                            {STYLE_LABEL[c.display_style] ?? c.display_style}
                          </span>
                        </div>
                        <div style={{ color: "var(--text-tertiary)", fontSize: 11 }}>
                          {SLOT_LABEL[c.placement] ?? c.placement}
                          {slotCounts[c.placement] > 1 ? ` · carousel of ${slotCounts[c.placement]}` : ""}
                        </div>
                      </td>
                      <td style={{ padding: "12px 14px", color: "var(--text-secondary)", fontSize: 12 }}>
                        {c.cta_label
                          ? <>{c.cta_label}<div style={{ color: "var(--text-tertiary)", fontSize: 11 }}>{c.cta_deeplink}</div></>
                          : <span style={{ color: "var(--text-tertiary)" }}>None</span>}
                      </td>
                      <td style={{ padding: "12px 14px", color: "var(--text-secondary)", fontSize: 12 }}>
                        {c.target_zipcodes.length > 0
                          ? `${c.target_zipcodes.length} PIN code(s)`
                          : <span style={{ color: "var(--text-tertiary)" }}>Everyone</span>}
                      </td>
                      <td style={{ padding: "12px 14px", color: "var(--text-secondary)", fontSize: 12 }}>
                        {c.starts_at || c.ends_at ? (
                          <>
                            {c.starts_at ? new Date(c.starts_at).toLocaleDateString() : "Now"}
                            {" → "}
                            {c.ends_at ? new Date(c.ends_at).toLocaleDateString() : "No end"}
                          </>
                        ) : <span style={{ color: "var(--text-tertiary)" }}>Always</span>}
                      </td>
                      <td style={{ padding: "12px 14px" }}>
                        <Badge variant={v.variant} size="sm">{v.label}</Badge>
                      </td>
                      <td style={{ padding: "12px 14px", textAlign: "right" }}>
                        <RowActions
                          onEdit={() => { setEditing(c); setCreating(false); setForm(formFrom(c)); }}
                          onDelete={() => remove.execute(c)}
                          extra={
                            <Btn variant="ghost" size="sm" onClick={() => toggle.execute(c)}>
                              {c.is_enabled ? "Turn off" : "Turn on"}
                            </Btn>
                          }
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <Modal
        open={creating || editing !== null}
        onClose={closeModal}
        title={editing ? "Edit banner" : "New banner"}
        size="lg"
      >
        <div style={{ display: "grid", gap: 12 }}>
          <Input
            label="Internal name" required value={form.internal_name}
            hint="For your team only — never shown to customers."
            onChange={v => setForm(f => ({ ...f, internal_name: v }))}
          />
          <Input label="Eyebrow" value={form.eyebrow}
            hint="Small line above the title, e.g. LIMITED TIME."
            onChange={v => setForm(f => ({ ...f, eyebrow: v }))} />
          <Input label="Title" required value={form.title}
            onChange={v => setForm(f => ({ ...f, title: v }))} />
          <Input label="Description" value={form.description}
            onChange={v => setForm(f => ({ ...f, description: v }))} />

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Select
              label="Style" value={form.display_style}
              options={CAMPAIGN_STYLES.map(o => ({ value: o.value, label: o.label }))}
              onChange={v => setForm(f => ({ ...f, display_style: v }))}
            />
            <Select
              label="Slot on Home" value={form.placement}
              options={CAMPAIGN_PLACEMENTS.map(o => ({ value: o.value, label: o.label }))}
              onChange={v => setForm(f => ({ ...f, placement: v }))}
            />
          </div>
          <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: 0 }}>
            {slotCounts[form.placement] > 0
              ? `${slotCounts[form.placement]} live banner(s) already in this slot — they become a swipeable carousel.`
              : "This slot is empty, so the banner will show on its own."}
            {" Slots can be re-ordered or switched off on the Home Layout page."}
          </p>

          {form.display_style === "festival" ? (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <Input
                label="Badge" value={form.badge_text}
                hint="Small pill above the title, e.g. Diwali Special."
                onChange={v => setForm(f => ({ ...f, badge_text: v }))}
              />
              <Input
                label="Accent colour" value={form.accent_color} placeholder="#f59e0b"
                hint="Hex. The card, badge and button are painted in it; the app picks a readable label colour automatically."
                onChange={v => setForm(f => ({ ...f, accent_color: v }))}
              />
            </div>
          ) : form.display_style === "strip" ? (
            <Input
              label="Accent colour" value={form.accent_color} placeholder="#0ea5e9"
              hint="Hex. Tints the strip and its icon."
              onChange={v => setForm(f => ({ ...f, accent_color: v }))}
            />
          ) : null}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <IconPicker
              label="Artwork (light mode)" context="banner_artwork" size={88} maxMb={5}
              value={form.artwork_url_light}
              onChange={v => setForm(f => ({ ...f, artwork_url_light: v ?? "" }))}
            />
            <IconPicker
              label="Artwork (dark mode)" context="banner_artwork" size={88} maxMb={5}
              value={form.artwork_url_dark}
              onChange={v => setForm(f => ({ ...f, artwork_url_dark: v ?? "" }))}
            />
          </div>
          <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: 0 }}>
            No artwork? The banner still renders as a clean text card — artwork is optional, not required.
          </p>

          <Input label="Button label" value={form.cta_label}
            hint="Leave empty for a plain informational banner with no button."
            onChange={v => setForm(f => ({ ...f, cta_label: v }))} />
          <DeeplinkPicker
            value={form.cta_deeplink}
            onChange={v => setForm(f => ({ ...f, cta_deeplink: v }))}
          />

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Input label="Priority" type="number" value={form.priority}
              hint="Lower shows first." onChange={v => setForm(f => ({ ...f, priority: v }))} />
            <Input label="Target PIN codes" value={form.target_zipcodes}
              hint="Comma-separated. Leave empty to show everywhere."
              onChange={v => setForm(f => ({ ...f, target_zipcodes: v }))} />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Input label="Starts (optional)" type="datetime-local" value={form.starts_at}
              onChange={v => setForm(f => ({ ...f, starts_at: v }))} />
            <Input label="Ends (optional)" type="datetime-local" value={form.ends_at}
              onChange={v => setForm(f => ({ ...f, ends_at: v }))} />
          </div>
          <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: 0 }}>
            Leave the schedule empty to run indefinitely. A banner outside its
            window stays hidden from customers even while it is turned on.
          </p>

          {(formError || save.error) && (
            <p style={{ color: "var(--danger-text)", fontSize: 12.5, margin: 0 }}>
              {formError ?? save.error}
            </p>
          )}

          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 4 }}>
            <Btn variant="ghost" onClick={closeModal}>Cancel</Btn>
            <Btn onClick={() => save.execute()} disabled={save.loading}>
              {save.loading ? <Spinner size={14} /> : editing ? "Save changes" : "Create banner"}
            </Btn>
          </div>
        </div>
      </Modal>
    </div>
  );
}

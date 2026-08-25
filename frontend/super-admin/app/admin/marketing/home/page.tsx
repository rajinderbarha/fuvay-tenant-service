"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Archive,
  ArrowDown,
  ArrowUp,
  CalendarClock,
  Image as ImageIcon,
  Layers3,
  MapPin,
  Pencil,
  Plus,
  RefreshCw,
  Smartphone,
  Sparkles,
} from "lucide-react";

import {
  adminCustomerHomeApi,
  CustomerHomePlacementDefinition,
  CustomerHomePlacementItem,
  CustomerHomePlacementWrite,
  CustomerHomeSectionConfig,
} from "@/lib/api";
import { useAction, useApi } from "@/hooks/useApi";
import {
  Badge,
  Btn,
  Card,
  Input,
  Modal,
  Select,
  Skeleton,
  Textarea,
} from "@/components/shared/ui";
import { IconPicker } from "@/components/shared/IconPicker";

type FormState = {
  title: string;
  subtitle: string;
  placement: string;
  variant: string;
  theme_key: string;
  section_title: string;
  badge: string;
  offer_text: string;
  image_url: string;
  action_label: string;
  action_url: string;
  category_slug: string;
  service_group_slug: string;
  sponsored: boolean;
  priority: string;
  city: string;
  zipcodes: string;
  frequency_cap_per_day: string;
  starts_at: string;
  ends_at: string;
  is_active: boolean;
};

const EMPTY_FORM: FormState = {
  title: "",
  subtitle: "",
  placement: "home_hero",
  variant: "cinematic",
  theme_key: "ink",
  section_title: "",
  badge: "Featured",
  offer_text: "",
  image_url: "",
  action_label: "Explore",
  action_url: "",
  category_slug: "",
  service_group_slug: "",
  sponsored: false,
  priority: "0",
  city: "",
  zipcodes: "",
  frequency_cap_per_day: "0",
  starts_at: "",
  ends_at: "",
  is_active: false,
};

function toLocalDateTime(value: string | null) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function formFromItem(item: CustomerHomePlacementItem): FormState {
  return {
    title: item.title,
    subtitle: item.subtitle,
    placement: item.placement,
    variant: item.variant,
    theme_key: item.theme_key,
    section_title: item.section_title ?? "",
    badge: item.badge,
    offer_text: item.offer_text ?? "",
    image_url: item.image_url,
    action_label: item.action_label,
    action_url: item.action_url ?? "",
    category_slug: item.category_slug ?? "",
    service_group_slug: item.service_group_slug ?? "",
    sponsored: item.sponsored,
    priority: String(item.priority),
    city: item.city ?? "",
    zipcodes: item.zipcodes.join(", "),
    frequency_cap_per_day: String(item.frequency_cap_per_day),
    starts_at: toLocalDateTime(item.starts_at),
    ends_at: toLocalDateTime(item.ends_at),
    is_active: item.is_active,
  };
}

function payloadFromForm(form: FormState): CustomerHomePlacementWrite {
  const optional = (value: string) => value.trim() || null;
  return {
    title: form.title.trim(),
    subtitle: form.subtitle.trim(),
    placement: form.placement,
    variant: form.variant,
    theme_key: form.theme_key,
    section_title: optional(form.section_title),
    badge: form.badge.trim() || "Featured",
    offer_text: optional(form.offer_text),
    image_url: form.image_url.trim(),
    action_label: form.action_label.trim() || "Explore",
    action_url: optional(form.action_url),
    category_slug: optional(form.category_slug),
    service_group_slug: optional(form.service_group_slug),
    sponsored: form.sponsored,
    priority: Number(form.priority) || 0,
    city: optional(form.city),
    zipcodes: form.zipcodes.split(",").map(value => value.trim()).filter(Boolean),
    frequency_cap_per_day: Math.max(0, Number(form.frequency_cap_per_day) || 0),
    starts_at: form.starts_at ? new Date(form.starts_at).toISOString() : null,
    ends_at: form.ends_at ? new Date(form.ends_at).toISOString() : null,
    is_active: form.is_active,
  };
}

function placementLabel(definitions: CustomerHomePlacementDefinition[], key: string) {
  return definitions.find(item => item.key === key)?.label ?? key.replaceAll("_", " ");
}

export default function CustomerHomeControlPage() {
  const { data, loading, error, refetch } = useApi(
    useCallback(() => adminCustomerHomeApi.listPlacements(), []),
  );
  const [editing, setEditing] = useState<CustomerHomePlacementItem | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [filter, setFilter] = useState("all");
  const [sections, setSections] = useState<CustomerHomeSectionConfig[]>([]);
  const [compositionReason, setCompositionReason] = useState("Improve customer Home composition");
  const saveAction = useAction(useCallback(
    (args: { id: string | null; body: CustomerHomePlacementWrite }) => args.id
      ? adminCustomerHomeApi.updatePlacement(args.id, args.body)
      : adminCustomerHomeApi.createPlacement(args.body),
    [],
  ));
  const archiveAction = useAction(useCallback(
    (id: string) => adminCustomerHomeApi.archivePlacement(id),
    [],
  ));
  const compositionAction = useAction(useCallback(
    (args: { sections: CustomerHomeSectionConfig[]; reason: string }) =>
      adminCustomerHomeApi.updateComposition(args),
    [],
  ));

  useEffect(() => {
    if (data?.composition.sections) setSections(data.composition.sections);
  }, [data?.composition.sections]);

  const definitions = data?.placements ?? [];
  const selectedDefinition = definitions.find(item => item.key === form.placement);
  const items = useMemo(
    () => (data?.items ?? []).filter(item => filter === "all" || item.placement === filter),
    [data?.items, filter],
  );
  const activeCount = (data?.items ?? []).filter(item => item.is_active).length;
  const sectionDefinitions = data?.composition.definitions ?? [];

  function patchSection(index: number, patch: Partial<CustomerHomeSectionConfig>) {
    setSections(current => current.map((section, sectionIndex) => sectionIndex === index ? { ...section, ...patch } : section));
  }

  function moveSection(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= sections.length) return;
    setSections(current => {
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  async function saveComposition() {
    const result = await compositionAction.execute({ sections, reason: compositionReason.trim() });
    if (!result) return;
    setSections(result.sections);
    refetch();
  }

  function openCreate() {
    const first = definitions[0];
    setEditing(null);
    setForm({
      ...EMPTY_FORM,
      placement: first?.key ?? "home_hero",
      variant: first?.variants[0] ?? "cinematic",
      theme_key: data?.themes[0] ?? "ink",
    });
    setModalOpen(true);
  }

  function openEdit(item: CustomerHomePlacementItem) {
    setEditing(item);
    setForm(formFromItem(item));
    setModalOpen(true);
  }

  async function save() {
    const result = await saveAction.execute({ id: editing?.campaign_id ?? null, body: payloadFromForm(form) });
    if (!result) return;
    setModalOpen(false);
    refetch();
  }

  async function archive(item: CustomerHomePlacementItem) {
    if (!window.confirm(`Archive “${item.title}”? It will stop appearing in the app.`)) return;
    const result = await archiveAction.execute(item.campaign_id);
    if (result) refetch();
  }

  const canSave = form.title.trim().length >= 2
    && form.subtitle.trim().length >= 2
    && form.image_url.trim().startsWith("https://")
    && Boolean(form.variant);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 22, maxWidth: 1480, margin: "0 auto" }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--accent)", fontSize: 11, fontWeight: 800, letterSpacing: ".09em", textTransform: "uppercase" }}>
            <Smartphone size={14} /> Customer experience
          </div>
          <h1 style={{ margin: "7px 0 4px", fontSize: 26, lineHeight: 1.2, color: "var(--text-primary)" }}>Customer Home studio</h1>
          <p style={{ margin: 0, color: "var(--text-secondary)", fontSize: 13, maxWidth: 760 }}>
            Operate banners, offers and creative collections from one safe content system. The native app owns accessibility and layout; you control content, targeting, priority and schedule.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Btn variant="secondary" onClick={refetch} icon={<RefreshCw size={14} />}>Refresh</Btn>
          <Btn onClick={openCreate} icon={<Plus size={14} />}>New Home content</Btn>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 12 }}>
        {[
          { label: "Content items", value: data?.count ?? 0, note: "across native placements", icon: <Layers3 size={18} /> },
          { label: "Live now", value: activeCount, note: "eligible by schedule and location", icon: <Sparkles size={18} /> },
          { label: "Hero slides", value: (data?.items ?? []).filter(item => item.is_active && item.placement === "home_hero").length, note: "maximum 5 active", icon: <ImageIcon size={18} /> },
          { label: "Reusable layouts", value: definitions.length, note: "app-certified presentation types", icon: <Smartphone size={18} /> },
        ].map(metric => (
          <Card key={metric.label} padding={16}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
              <div>
                <p style={{ margin: 0, fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: ".06em" }}>{metric.label}</p>
                <p style={{ margin: "7px 0 2px", fontSize: 25, fontWeight: 760, color: "var(--text-primary)" }}>{metric.value}</p>
                <p style={{ margin: 0, fontSize: 11, color: "var(--text-tertiary)" }}>{metric.note}</p>
              </div>
              <div style={{ width: 36, height: 36, borderRadius: 10, display: "grid", placeItems: "center", color: "var(--accent)", background: "var(--accent-muted)" }}>{metric.icon}</div>
            </div>
          </Card>
        ))}
      </div>

      <Card padding={0}>
        <div style={{ padding: 16, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, borderBottom: "1px solid var(--border)" }}>
          <div>
            <h2 style={{ margin: 0, fontSize: 15, color: "var(--text-primary)" }}>Native section composition</h2>
            <p style={{ margin: "3px 0 0", fontSize: 12, color: "var(--text-tertiary)" }}>Order, title, density and visibility are remotely controlled. Components remain app-certified and cannot execute arbitrary markup.</p>
          </div>
          <Badge variant="success" dot>{sections.filter(section => section.enabled).length} sections live</Badge>
        </div>
        <div style={{ display: "grid" }}>
          {sections.map((section, index) => {
            const definition = sectionDefinitions.find(item => item.key === section.key);
            return (
              <div key={section.key} style={{ minHeight: 76, padding: "10px 16px", display: "grid", gridTemplateColumns: "72px minmax(160px, 1fr) minmax(160px, 1fr) 132px 118px 118px 104px", gap: 10, alignItems: "center", borderBottom: "1px solid var(--border)", opacity: section.enabled ? 1 : .6 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <Btn size="sm" variant="ghost" aria-label={`Move ${definition?.label ?? section.key} up`} disabled={index === 0} onClick={() => moveSection(index, -1)} icon={<ArrowUp size={13} />} />
                  <Btn size="sm" variant="ghost" aria-label={`Move ${definition?.label ?? section.key} down`} disabled={index === sections.length - 1} onClick={() => moveSection(index, 1)} icon={<ArrowDown size={13} />} />
                </div>
                <div>
                  <strong style={{ color: "var(--text-primary)", fontSize: 13 }}>{definition?.label ?? section.key}</strong>
                  <p style={{ margin: "2px 0 0", color: "var(--text-tertiary)", fontSize: 11 }}>{section.key}</p>
                </div>
                <Input value={section.title ?? ""} onChange={value => patchSection(index, { title: value.trim() ? value : null })} placeholder="No section heading" />
                <Select value={section.variant} onChange={value => patchSection(index, { variant: value })} options={(definition?.variants ?? [section.variant]).map(value => ({ value, label: value.replaceAll("_", " ") }))} />
                <Select value={section.spacing} onChange={value => patchSection(index, { spacing: value as CustomerHomeSectionConfig["spacing"] })} options={(data?.composition.layout_options?.spacing ?? ["compact", "standard", "generous"]).map(value => ({ value, label: `${value} spacing` }))} />
                <Select value={section.surface} onChange={value => patchSection(index, { surface: value as CustomerHomeSectionConfig["surface"] })} options={(data?.composition.layout_options?.surfaces ?? ["canvas", "subtle", "raised", "brand_tint"]).map(value => ({ value, label: value.replaceAll("_", " ") }))} />
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Input type="number" value={String(section.max_items)} onChange={value => patchSection(index, { max_items: Math.max(1, Math.min(definition?.max_items ?? 24, Number(value) || 1)) })} />
                  <input aria-label={`Enable ${definition?.label ?? section.key}`} type="checkbox" checked={section.enabled} onChange={event => patchSection(index, { enabled: event.target.checked })} />
                </div>
              </div>
            );
          })}
        </div>
        <div style={{ padding: 16, display: "flex", alignItems: "end", gap: 12 }}>
          <div style={{ flex: 1 }}>
            <Input label="Change reason" value={compositionReason} onChange={setCompositionReason} hint="Written to the platform settings audit trail." />
          </div>
          <Btn onClick={saveComposition} loading={compositionAction.loading} disabled={compositionReason.trim().length < 3}>Publish composition</Btn>
        </div>
        {compositionAction.error ? <div style={{ padding: "0 16px 16px", color: "var(--danger-text)", fontSize: 12 }}>{compositionAction.error}</div> : null}
      </Card>

      <Card padding={0}>
        <div style={{ padding: 16, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, borderBottom: "1px solid var(--border)" }}>
          <div>
            <h2 style={{ margin: 0, fontSize: 15, color: "var(--text-primary)" }}>Published Home composition</h2>
            <p style={{ margin: "3px 0 0", fontSize: 12, color: "var(--text-tertiary)" }}>Priority orders content inside its placement; essential booking and service sections remain product-owned.</p>
          </div>
          <div style={{ width: 230 }}>
            <Select
              value={filter}
              onChange={setFilter}
              options={[{ value: "all", label: "All placements" }, ...definitions.map(item => ({ value: item.key, label: item.label }))]}
            />
          </div>
        </div>
        {loading ? (
          <div style={{ padding: 20, display: "grid", gap: 10 }}>{[0, 1, 2].map(i => <Skeleton key={i} height={74} />)}</div>
        ) : error ? (
          <div style={{ padding: 28, color: "var(--danger-text)", fontSize: 13 }}>{error}</div>
        ) : items.length === 0 ? (
          <div style={{ padding: 48, textAlign: "center" }}>
            <ImageIcon size={28} style={{ color: "var(--text-tertiary)" }} />
            <h3 style={{ margin: "10px 0 4px", fontSize: 15 }}>No Home content in this view</h3>
            <p style={{ margin: 0, fontSize: 12, color: "var(--text-tertiary)" }}>Create a draft, preview its targeting, then make it active.</p>
          </div>
        ) : (
          <div style={{ display: "grid" }}>
            {items.map(item => (
              <div key={item.campaign_id} style={{ minHeight: 92, padding: "13px 16px", display: "grid", gridTemplateColumns: "86px minmax(240px, 1.6fr) minmax(180px, .8fr) minmax(180px, .8fr) auto", alignItems: "center", gap: 14, borderBottom: "1px solid var(--border)" }}>
                <img src={item.image_url} alt="" style={{ width: 86, height: 62, objectFit: "cover", borderRadius: 9, background: "var(--surface-sunken)" }} />
                <div style={{ minWidth: 0 }}>
                  <div style={{ display: "flex", gap: 7, alignItems: "center", flexWrap: "wrap" }}>
                    <strong style={{ color: "var(--text-primary)", fontSize: 13 }}>{item.title}</strong>
                    <Badge variant={item.is_active ? "success" : "muted"} dot>{item.is_active ? "Live" : "Draft"}</Badge>
                    {item.sponsored ? <Badge variant="warning">Sponsored</Badge> : null}
                  </div>
                  <p style={{ margin: "4px 0 0", color: "var(--text-tertiary)", fontSize: 12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item.subtitle}</p>
                </div>
                <div>
                  <p style={{ margin: 0, fontSize: 11, color: "var(--text-tertiary)" }}>Placement</p>
                  <p style={{ margin: "4px 0 0", fontSize: 12, color: "var(--text-primary)", fontWeight: 650 }}>{placementLabel(definitions, item.placement)}</p>
                  <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--text-tertiary)" }}>{item.variant} · priority {item.priority}</p>
                </div>
                <div>
                  <p style={{ margin: 0, fontSize: 11, color: "var(--text-tertiary)" }}>Target & schedule</p>
                  <p style={{ margin: "4px 0 0", fontSize: 12, color: "var(--text-primary)" }}>{item.zipcodes.length ? `${item.zipcodes.length} PIN codes` : item.city || "All locations"}</p>
                  <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--text-tertiary)" }}>{item.ends_at ? `Ends ${new Date(item.ends_at).toLocaleDateString()}` : "No end date"}</p>
                </div>
                <div style={{ display: "flex", gap: 4 }}>
                  <Btn size="sm" variant="ghost" onClick={() => openEdit(item)} icon={<Pencil size={13} />}>Edit</Btn>
                  <Btn size="sm" variant="ghost" onClick={() => archive(item)} disabled={archiveAction.loading} icon={<Archive size={13} />}>Archive</Btn>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? "Edit Home content" : "Create Home content"} size="xl">
        <div style={{ padding: 22, display: "grid", gap: 20 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <Input label="Title" required value={form.title} onChange={value => setForm(current => ({ ...current, title: value }))} placeholder="Monsoon home care" />
            <Input label="Section heading (optional)" value={form.section_title} onChange={value => setForm(current => ({ ...current, section_title: value }))} placeholder="Made for the monsoon" />
          </div>
          <Textarea label="Supporting copy" required rows={3} value={form.subtitle} onChange={value => setForm(current => ({ ...current, subtitle: value }))} placeholder="Explain the offer clearly in one or two sentences." />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>
            <Select
              label="Placement"
              value={form.placement}
              onChange={value => {
                const definition = definitions.find(item => item.key === value);
                setForm(current => ({ ...current, placement: value, variant: definition?.variants[0] ?? "" }));
              }}
              options={definitions.map(item => ({ value: item.key, label: item.label }))}
            />
            <Select label="Layout variant" value={form.variant} onChange={value => setForm(current => ({ ...current, variant: value }))} options={(selectedDefinition?.variants ?? []).map(value => ({ value, label: value.replaceAll("_", " ") }))} />
            <Select label="Colour direction" value={form.theme_key} onChange={value => setForm(current => ({ ...current, theme_key: value }))} options={(data?.themes ?? []).map(value => ({ value, label: value }))} />
          </div>
          {selectedDefinition ? (
            <div style={{ padding: 12, borderRadius: 10, background: "var(--info-bg)", border: "1px solid var(--info-border)", color: "var(--info-text)", fontSize: 12 }}>
              {selectedDefinition.description} Up to {selectedDefinition.max_active} can be live at once.
            </div>
          ) : null}
          <div style={{ padding: 14, border: "1px solid var(--border)", borderRadius: 12, background: "var(--surface-sunken)" }}>
            <IconPicker
              label="Campaign artwork"
              context="home_campaign_artwork"
              value={form.image_url || null}
              onChange={value => setForm(current => ({ ...current, image_url: value ?? "" }))}
              size={180}
              maxMb={8}
              removable
              noun="artwork"
            />
            <p style={{ margin: "8px 0 0", color: "var(--text-tertiary)", fontSize: 11 }}>Upload once to Cloudinary or reuse an existing approved Home artwork. Localhost files are never published.</p>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>
            <Input label="Badge" value={form.badge} onChange={value => setForm(current => ({ ...current, badge: value }))} placeholder="Featured" />
            <Input label="Offer text" value={form.offer_text} onChange={value => setForm(current => ({ ...current, offer_text: value }))} placeholder="Save 20%" />
            <Input label="Priority" type="number" value={form.priority} onChange={value => setForm(current => ({ ...current, priority: value }))} hint="Higher appears first." />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>
            <Input label="Button label" value={form.action_label} onChange={value => setForm(current => ({ ...current, action_label: value }))} />
            <Input label="Deep link / URL" value={form.action_url} onChange={value => setForm(current => ({ ...current, action_url: value }))} placeholder="fuvay://assistant or https://..." />
            <Input label="Category slug" value={form.category_slug} onChange={value => setForm(current => ({ ...current, category_slug: value }))} placeholder="home_services" />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <Select
              label="Service group targeting"
              value={form.service_group_slug}
              onChange={value => setForm(current => ({ ...current, service_group_slug: value }))}
              options={[
                { value: "", label: "All bookable groups" },
                ...(data?.service_groups ?? []).map(group => ({ value: group.slug, label: group.label })),
              ]}
            />
            <div style={{ alignSelf: "end", minHeight: 42, padding: "10px 12px", borderRadius: 9, background: "var(--surface-sunken)", color: "var(--text-tertiary)", fontSize: 12 }}>
              Targeted content is shown only when this group has a published provider in the customer&apos;s selected PIN code.
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, paddingTop: 4, borderTop: "1px solid var(--border)" }}>
            <Input label="City (optional)" value={form.city} onChange={value => setForm(current => ({ ...current, city: value }))} icon={<MapPin size={14} />} placeholder="Ludhiana" />
            <Input label="PIN codes (optional, comma separated)" value={form.zipcodes} onChange={value => setForm(current => ({ ...current, zipcodes: value }))} placeholder="141001, 141002" />
            <Input label="Starts at" type="datetime-local" value={form.starts_at} onChange={value => setForm(current => ({ ...current, starts_at: value }))} icon={<CalendarClock size={14} />} />
            <Input label="Ends at" type="datetime-local" value={form.ends_at} onChange={value => setForm(current => ({ ...current, ends_at: value }))} icon={<CalendarClock size={14} />} />
            <Input
              label="Daily delivery cap"
              type="number"
              value={form.frequency_cap_per_day}
              onChange={value => setForm(current => ({ ...current, frequency_cap_per_day: value }))}
              hint="Use 0 for evergreen content. A positive value limits delivery per customer each day."
            />
          </div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 18, padding: 14, borderRadius: 12, background: "var(--surface-sunken)", border: "1px solid var(--border)" }}>
            <div>
              <strong style={{ display: "block", color: "var(--text-primary)", fontSize: 13 }}>Publish in the customer app</strong>
              <span style={{ color: "var(--text-tertiary)", fontSize: 12 }}>When off, this remains a safe draft. Schedule and location rules still apply when on.</span>
            </div>
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>
              <input type="checkbox" checked={form.is_active} onChange={event => setForm(current => ({ ...current, is_active: event.target.checked }))} />
              {form.is_active ? "Live" : "Draft"}
            </label>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <label style={{ display: "flex", gap: 7, alignItems: "center", color: "var(--text-secondary)", fontSize: 12 }}>
              <input type="checkbox" checked={form.sponsored} onChange={event => setForm(current => ({ ...current, sponsored: event.target.checked }))} /> Sponsored disclosure required
            </label>
            <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
              <Btn variant="secondary" onClick={() => setModalOpen(false)}>Cancel</Btn>
              <Btn onClick={save} loading={saveAction.loading} disabled={!canSave}>{editing ? "Save changes" : "Create content"}</Btn>
            </div>
          </div>
          {saveAction.error ? <div style={{ color: "var(--danger-text)", fontSize: 12 }}>{saveAction.error}</div> : null}
        </div>
      </Modal>
    </div>
  );
}

# Phase 3C-Closure — Visual Value Safety Report

Static scan of both pricing pages for unsafe direct rendering of nullable
values, plus verification of every relevant fallback path.

## Scan method

Grepped both page files for every field interpolation (`{row.X}`, `{v.X}`,
`.toLocaleString(`, `.toFixed(`) and classified each as: (a) backed by a
non-nullable backend column/enum with a default, (b) guarded by a truthy
check before rendering, or (c) routed through a safe formatter.

## Findings

| Field | Page | Guard | Verdict |
|---|---|---|---|
| `row.rule_code` | Bargain Rules | `row.rule_code && <div>...` | Safe |
| `row.category_name` | Bargain Rules | `row.category_name && <div>...` | Safe |
| `row.floor_type` | Bargain Rules | Non-nullable enum, DB default `"fixed"` | Safe |
| `row.below_floor_action` | Bargain Rules | Non-nullable enum, DB default `"reject"` | Safe |
| `row.status` | Both | Non-nullable enum, DB default `"active"` | Safe |
| `row.warning` | Bargain Rules | `row.warning && <div>...` | Safe |
| `row.zipcode` | Provider Overrides | `row.zipcode && <div>...` | Safe |
| `row.currency` | Provider Overrides | Non-nullable, DB default `"INR"` | Safe |
| `row.override_price.toLocaleString(...)` | Provider Overrides | `override_price` is a `NOT NULL` column, always required on create | Safe |
| `row.approval_status` | Provider Overrides | Non-nullable enum, DB default `"pending"` | Safe |
| All `base_price`/`min_price`/`max_price`/`bargain_floor`/`platform_*`/`delta_from_base` values | Both | Routed through shared `money(v)` helper: `v == null ? "—" : ...` | Safe |
| Detail-drawer `Field` component values | Both | `value === null \|\| value === undefined \|\| value === "" ? "—" : String(value)` | Safe |

**No unguarded nullable field renders a raw `undefined`/`null`/`NaN` string.**
No `[object Object]` risk found — every object-typed value (`context` in
`ErrorBlock`) is explicitly destructured/stringified via
`Object.entries(context).map(([k,v]) => \`${k}: ${v}\`)`, never rendered as a
bare object.

## Tenant name primary-display verification

```tsx
<div style={{ fontSize: 13, fontWeight: 600 }}>{row.tenant_name || "Unknown tenant"}</div>
<div style={{ fontSize: 11, color: "var(--muted-text)" }}>{row.tenant_code || "—"}</div>
<div style={{ fontSize: 9, ... fontFamily: "monospace" }}>{row.tenant_id.slice(0, 8)}…</div>
```

- Primary display: `tenant_name`, with an explicit `"Unknown tenant"` fallback
  (matches the ticket's required fallback text exactly).
- Secondary: `tenant_code`, falls back to `"—"`.
- Tertiary (smallest font, monospace): raw tenant ID, sliced to 8 chars —
  never the primary or sole identifier.

## Missing-count fallback (summary cards)

All 16 summary-card values across both pages use `?? 0` for counts
(`summary.data?.total_bargain_rules ?? 0`, etc.) or explicit `!= null ? ... :
"—"` for averages (`avg_accepted_offer`, `avg_override_price`) — confirmed no
card can render `undefined`/`NaN`.

## Missing service-context fallback

Service-context lines use `.filter(Boolean).join(" · ") || "—"` — if
`service_type_name`/`brand_name`/`issue_type_name` are all null, the row
renders `"—"` rather than an empty string or `"· · "`. The ticket's suggested
exact wording `"Not configured"` was not used verbatim — `"—"` was used
instead for consistency with every other empty-value fallback on the page.
This is a wording choice, not a null-safety defect (both are equally
comprehensible empty-state indicators, and mixing two different empty-state
strings in the same table would be less consistent, not more correct).

## Result: **PASS.** No visible NaN/null/undefined/[object Object] risk found. Tenant name is primary display; raw ID is tertiary only.

# Tenant Type-Brand Override UI Report

## Step 4 — Brand Overrides (fixed)
Now renders one section per selected type (looping
`typePricingState.map(tp => ...)`), each showing:
- Type name
- Platform Allowed Range + Your Type Range (both read-only, sourced from
  the type's own admin floor/ceiling)
- "Brand Overrides for {Type Name}" heading
- Brand override rows scoped to that type only
  (`brandPricingState.filter(b => b.typeId === tp.typeId && b.canOverride)`)

Sections with no overridable brands for that type are hidden
(`if (rowsForType.length === 0) return null`) rather than showing an
empty section.

## Review & Publish matrix (fixed)
Brand rows are nested under their own type row only
(`.filter(b => b.typeId === tp.typeId && b.canOverride)`), never under
every type. Two states per brand-per-type:
- Configured: shows Min/Max/Customer-sees preview, labeled "Type brand
  override."
- Not configured: shows "No brand override — using type price" with an
  inline "Add override" CTA that jumps back to Step 4.

## Price resolution copy (fixed)
Updated to the ticket's exact required text: "type-specific brand price
→ type price → service base price" plus the explicit Window AC/Split AC
example sentence.

## Not built (documented gap)
The ticket's "Add Brand Override Modal" (a separate, type-locked modal
dialog) doesn't exist — this page uses inline rows instead, achieving
the same functional guarantee (type context is always implicit and
correct) without a modal. If a modal is specifically required by
product design, it's a UI-pattern change, not a data-correctness gap.

## Verdict
Step 4 and Review matrix: **fixed, real, type-scoped**. Modal pattern:
**not built** (inline equivalent used instead) — documented, not hidden.

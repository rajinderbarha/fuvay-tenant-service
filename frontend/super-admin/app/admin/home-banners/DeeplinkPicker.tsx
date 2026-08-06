"use client";
/**
 * Picker for a banner's `cta_deeplink`, replacing a bare free-text field.
 *
 * Real bug this closes: `app://category/{X}` must carry the category
 * SLUG — the mobile app's deep-link resolver
 * (mobile/customer-app/src/domain/campaignDeepLink.ts) matches it against
 * `bookable_categories[].slug`, never an id. A free-text field with only a
 * text hint invites exactly the mistake of pasting a category_id (UUID)
 * instead, which silently leaves the button permanently disabled for every
 * customer — no error anywhere, because a UUID also happens to satisfy the
 * "starts with app://category/" check. Selecting from a real list makes
 * that mistake impossible.
 */
import { useCallback } from "react";
import { useApi } from "../../../hooks/useApi";
import { catalogApi } from "../../../lib/api";

const KIND_OPTIONS = [
  { value: "app://home", label: "Home screen" },
  { value: "app://category/", label: "A specific category" },
] as const;

function kindOf(deeplink: string): string {
  if (!deeplink) return "";
  if (deeplink.startsWith("app://category/")) return "app://category/";
  if (deeplink === "app://home") return "app://home";
  return "other"; // app://service/, app://booking/, app://offers -- no destination in the app yet
}

export default function DeeplinkPicker({
  value, onChange,
}: {
  value: string;
  onChange: (deeplink: string) => void;
}) {
  const { data } = useApi(useCallback(() => catalogApi.listCategories(true), []));
  const categories = data?.categories ?? [];
  const kind = kindOf(value);
  const selectedSlug = kind === "app://category/" ? value.slice("app://category/".length) : "";

  return (
    <div>
      <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 6 }}>Button destination</label>
      <div style={{ display: "flex", gap: 8 }}>
        <select
          value={kind === "other" ? "" : kind}
          onChange={(e) => {
            const next = e.target.value;
            onChange(next === "app://category/" ? "" : next);
          }}
          style={{
            flex: kind === "app://category/" ? "0 0 46%" : 1,
            padding: "9px 10px", borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-strong)", background: "var(--surface)",
            color: "var(--text-primary)", fontSize: 13,
          }}
        >
          <option value="" disabled>Choose a destination…</option>
          {KIND_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        {kind === "app://category/" && (
          <select
            value={selectedSlug}
            onChange={(e) => onChange(`app://category/${e.target.value}`)}
            style={{
              flex: 1, padding: "9px 10px", borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-strong)", background: "var(--surface)",
              color: "var(--text-primary)", fontSize: 13,
            }}
          >
            <option value="" disabled>Which category…</option>
            {categories.map(c => (
              <option key={c.category_id} value={c.slug}>{c.name}</option>
            ))}
          </select>
        )}
      </div>
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "6px 0 0" }}>
        Only real in-app destinations can be chosen, so a button can never come out disabled.
        Raw links (e.g. {CAMPAIGN_DEEPLINK_ONLY_HINT}) aren&apos;t supported yet from this screen.
      </p>
    </div>
  );
}

const CAMPAIGN_DEEPLINK_ONLY_HINT = "app://service/…, app://booking/…";

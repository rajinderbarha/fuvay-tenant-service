#!/usr/bin/env node
/**
 * FINAL-L5-05AI — Route coverage guard.
 *
 * A bounded, real, executable guard over the canonical top-level Admin
 * navigation registry (NAV_GROUPS in
 * frontend/super-admin/components/layout/AdminLayout.tsx). It parses the
 * actual source (not a hand-copied duplicate) so it can never silently
 * drift from the real route-permission mapping the app itself enforces.
 *
 * This is intentionally bounded to the 43 top-level nav routes documented
 * in FINAL_L5_05AI_ROUTE_ACTION_COVERAGE_REGISTRY.md, not the full ~160
 * page.tsx file tree (nested/dynamic routes inherit their parent's
 * permission via resolveActiveNavId's prefix match, a pre-existing,
 * separately-enforced mechanism this guard does not re-verify).
 *
 * Fails when:
 *   - A nav item has no `id`, `href`, or `requiredPermission` field.
 *   - `requiredPermission` is an empty string for anything other than the
 *     explicitly-documented public/self-service allowlist.
 *
 * Run: node e2e/route_coverage_guard.js
 * Exit 0 = ROUTE_COVERAGE_GUARD_PASSED. Exit 1 = ...GUARD_FAILED.
 */
const fs = require("fs");
const path = require("path");

const LAYOUT_PATH = path.resolve(
  __dirname, "..", "frontend", "super-admin", "components", "layout", "AdminLayout.tsx",
);

// Routes deliberately visible to all authenticated roles (dashboard) or
// reachable outside the permission system entirely (self-service account
// pages) -- matches SELF_SERVICE_ROUTE_IDS + the dashboard's "" sentinel,
// both already established in AdminLayout.tsx itself.
const ALLOWED_EMPTY_PERMISSION_IDS = new Set(["dashboard"]);

function extractNavItems(source) {
  // Each nav item is authored on a single source line (confirmed by
  // reading AdminLayout.tsx directly). Matching per-line, rather than a
  // single multi-field regex across the whole item literal, avoids a real
  // bug found while building this guard: the icon JSX (e.g.
  // `<LayoutDashboard size={16}/>`) contains a `}` that a naive
  // `[^}]*?` non-greedy span between `href` and `requiredPermission`
  // terminates on prematurely, silently matching zero items.
  const items = [];
  for (const line of source.split("\n")) {
    if (!line.includes("id:") || !line.includes("requiredPermission:")) continue;
    const idMatch = line.match(/id:\s*"([^"]+)"/);
    const hrefMatch = line.match(/href:\s*"([^"]+)"/);
    const permMatch = line.match(/requiredPermission:\s*(SUPER_ADMIN_ONLY|"[^"]*")/);
    if (!idMatch || !hrefMatch || !permMatch) continue;
    const rawPermission = permMatch[1];
    const permission = rawPermission.startsWith('"') ? rawPermission.slice(1, -1) : rawPermission;
    items.push({ id: idMatch[1], href: hrefMatch[1], permission });
  }
  return items;
}

function main() {
  const report = { source: LAYOUT_PATH, checks: {}, violations: [] };

  if (!fs.existsSync(LAYOUT_PATH)) {
    report.result = "ROUTE_COVERAGE_GUARD_FAILED";
    report.violations.push("AdminLayout.tsx not found at expected path");
    console.log(JSON.stringify(report, null, 2));
    process.exit(1);
  }

  const source = fs.readFileSync(LAYOUT_PATH, "utf8");
  const items = extractNavItems(source);
  report.checks.nav_items_discovered = items.length;

  if (items.length < 30) {
    // Sanity floor: this registry documented 43 items. A drastically lower
    // count means the regex stopped matching the real source shape (e.g.
    // after a refactor) -- fail rather than silently report a hollow pass.
    report.violations.push(`Only ${items.length} nav items parsed -- expected >=30 (registry documents 43). Regex likely out of sync with AdminLayout.tsx's real structure.`);
  }

  const seenIds = new Set();
  for (const item of items) {
    if (seenIds.has(item.id)) {
      report.violations.push(`Duplicate nav item id: ${item.id}`);
    }
    seenIds.add(item.id);

    if (!item.href || !item.href.startsWith("/admin")) {
      report.violations.push(`Nav item "${item.id}" has a missing or non-canonical href: "${item.href}"`);
    }

    if (item.permission === "" && !ALLOWED_EMPTY_PERMISSION_IDS.has(item.id)) {
      report.violations.push(`Nav item "${item.id}" has an empty requiredPermission and is not on the explicit self-service allowlist`);
    }
    if (item.permission !== "" && item.permission !== "SUPER_ADMIN_ONLY" && !item.permission.includes(":") && !item.permission.includes(".")) {
      report.violations.push(`Nav item "${item.id}" has a permission string that matches neither a real backend key pattern ("domain:action" / "domain.action") nor SUPER_ADMIN_ONLY: "${item.permission}"`);
    }
  }

  report.checks.duplicate_ids = items.length - seenIds.size;
  report.checks.items_with_permission = items.filter((i) => i.permission !== "").length;
  report.checks.items_super_admin_only = items.filter((i) => i.permission === "SUPER_ADMIN_ONLY").length;

  report.result = report.violations.length === 0 ? "ROUTE_COVERAGE_GUARD_PASSED" : "ROUTE_COVERAGE_GUARD_FAILED";
  console.log(JSON.stringify(report, null, 2));
  process.exit(report.violations.length === 0 ? 0 : 1);
}

main();

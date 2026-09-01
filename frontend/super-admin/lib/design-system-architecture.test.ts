import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import { join, relative, resolve } from "node:path";

const root = resolve(process.cwd());
const adminRoot = join(root, "app", "admin");

function sourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const path = join(directory, entry.name);
    return entry.isDirectory()
      ? sourceFiles(path)
      : /\.(ts|tsx)$/.test(entry.name)
        ? [path]
        : [];
  });
}

// The repository can live on a synced or antivirus-scanned Windows volume.
// Build each inventory once so the architecture guard never walks hundreds
// of feature files twice in the same run.
const adminSourceFiles = sourceFiles(adminRoot);
const componentSourceFiles = sourceFiles(join(root, "components"));
const canonicalComponentFiles = new Set([
  join(root, "components", "layout", "Breadcrumbs.tsx"),
  join(root, "components", "shared", "layout.tsx"),
  join(root, "components", "shared", "ui.tsx"),
]);
const featureComponentFiles = componentSourceFiles.filter(file => !canonicalComponentFiles.has(file));

describe("admin design-system architecture", () => {
  it("does not let feature pages reimplement shared UI primitives", () => {
    const primitiveDeclaration = /(?:export\s+)?(?:default\s+)?function\s+(Card|SummaryCard|MetricCard|KpiCard|KPICard|StatCard|DashCard|PageHeader|PageShell|Breadcrumbs|Btn|Button|Input|Select|Textarea|Modal|Badge|Pagination|EmptyState|ActionMenu)\b/g;
    const violations = [...adminSourceFiles, ...featureComponentFiles].flatMap(file => {
      const source = readFileSync(file, "utf8");
      return Array.from(source.matchAll(primitiveDeclaration), match =>
        `${relative(root, file)} defines ${match[1]}`,
      );
    });

    expect(violations, [
      "Feature pages must compose the canonical primitives exported by",
      "components/shared/ui.tsx and components/shared/layout.tsx.",
      "Add a prop or variant to the canonical component instead of creating a local copy.",
    ].join(" ")).toEqual([]);
  }, 90_000);

  it("does not import deleted or superseded component implementations", () => {
    const forbiddenImports = [
      "components/pricing/SummaryCard",
      "components/pricing/ActionMenu",
      "PkEmptyState",
    ];
    const violations = [...adminSourceFiles, ...componentSourceFiles].flatMap(file => {
      const source = readFileSync(file, "utf8");
      return forbiddenImports
        .filter(value => source.includes(value))
        .map(value => `${relative(root, file)} imports or references ${value}`);
    });

    expect(violations).toEqual([]);
  }, 90_000);

  it("keeps list pagination on the canonical Pagination component", () => {
    const handBuiltPager = /(?:Page\s*\{[^}]+\}\s*(?:of|\/)|>\s*(?:Prev|Previous|Next)\s*(?:→)?\s*<)/g;
    const wizardFiles = new Set([
      join(adminRoot, "marketing", "generate", "page.tsx"),
      join(adminRoot, "real-estate", "lead-drafts", "page.tsx"),
      join(adminRoot, "service-setup", "bulk-wizard", "page.tsx"),
      join(adminRoot, "service-setup", "bulk-wizard", "[draftId]", "page.tsx"),
      join(adminRoot, "service-setup", "templates", "page.tsx"),
    ]);
    const violations = adminSourceFiles
      .filter(file => !wizardFiles.has(file))
      .flatMap(file => Array.from(readFileSync(file, "utf8").matchAll(handBuiltPager), () => relative(root, file)));

    expect(violations, "List pages must use the shared Pagination component instead of page-specific controls.").toEqual([]);
  }, 90_000);

  it("keeps feature tables and row menus on the shared overflow-safe primitives", () => {
    const violations = [...adminSourceFiles, ...featureComponentFiles].flatMap(file => {
      const source = readFileSync(file, "utf8");
      const issues: string[] = [];
      if (/<table\b|<\/table>/.test(source)) issues.push("raw table markup");
      if (/(?:function|const)\s+\w*ActionMenu\b/.test(source)) issues.push("local action menu");
      if (/(?:function|const)\s+EnterpriseFilterBar\b/.test(source)) issues.push("local enterprise filter bar");
      return issues.map(issue => `${relative(root, file)} contains ${issue}`);
    });

    expect(violations, "Use TableSurface, ActionMenu, and EnterpriseFilterBar from @serviceos/design-system.").toEqual([]);
  }, 90_000);
});

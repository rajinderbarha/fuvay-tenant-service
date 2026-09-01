import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import { join, relative, resolve } from "node:path";

const root = resolve(process.cwd());

function sourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const path = join(directory, entry.name);
    return entry.isDirectory()
      ? sourceFiles(path)
      : /\.(ts|tsx)$/.test(entry.name) ? [path] : [];
  });
}

const appFiles = sourceFiles(join(root, "app"));
const componentFiles = sourceFiles(join(root, "components"));
const canonicalAdapters = new Set([
  join(root, "components", "layout", "Breadcrumbs.tsx"),
  join(root, "components", "shared", "layout.tsx"),
  join(root, "components", "shared", "ui.tsx"),
]);
const featureFiles = [...appFiles, ...componentFiles.filter(file => !canonicalAdapters.has(file))];

describe("tenant design-system architecture", () => {
  it("does not let feature pages reimplement shared primitives", () => {
    const declaration = /(?:export\s+)?(?:default\s+)?function\s+(Card|SummaryCard|MetricCard|KpiCard|KPICard|StatCard|DashCard|PageHeader|PageShell|Breadcrumbs|Btn|Button|Input|Select|Textarea|Modal|Badge|Pagination|EmptyState|ActionMenu)\b/g;
    const violations = featureFiles.flatMap(file => {
      const source = readFileSync(file, "utf8");
      return Array.from(source.matchAll(declaration), match => `${relative(root, file)} defines ${match[1]}`);
    });

    expect(violations, "Tenant features must compose @serviceos/design-system primitives instead of declaring visual copies.").toEqual([]);
  }, 90_000);

  it("keeps tables, row menus, and enterprise filters canonical", () => {
    const violations = featureFiles.flatMap(file => {
      const source = readFileSync(file, "utf8");
      const issues: string[] = [];
      if (/<table\b|<\/table>/.test(source)) issues.push("raw table markup");
      if (/(?:function|const)\s+\w*ActionMenu\b/.test(source)) issues.push("local action menu");
      if (/(?:function|const)\s+EnterpriseFilterBar\b/.test(source)) issues.push("local enterprise filter bar");
      return issues.map(issue => `${relative(root, file)} contains ${issue}`);
    });

    expect(violations, "Use TableSurface, ActionMenu, and EnterpriseFilterBar from the shared design system.").toEqual([]);
  }, 90_000);
});

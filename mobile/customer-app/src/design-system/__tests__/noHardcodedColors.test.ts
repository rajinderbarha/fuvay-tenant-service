import fs from "node:fs";
import path from "node:path";

function collectTsxFiles(directory: string): string[] {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      return entry.name === "__tests__" ? [] : collectTsxFiles(target);
    }
    return entry.isFile() && entry.name.endsWith(".tsx") ? [target] : [];
  });
}

describe("customer app design-token boundary", () => {
  it("keeps literal colors out of screens and components", () => {
    const sourceRoot = path.resolve(__dirname, "../..");
    const offenders = collectTsxFiles(sourceRoot).flatMap(file => {
      const source = fs.readFileSync(file, "utf8");
      return /#[0-9a-f]{3,8}\b|rgba?\(/i.test(source)
        ? [path.relative(sourceRoot, file)]
        : [];
    });

    expect(offenders).toEqual([]);
  });
});


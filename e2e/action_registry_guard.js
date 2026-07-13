// FINAL-L5-05AM: source-derived guard over the high-risk action registry.
// Parses the actual markdown table between the "## High-risk action
// registry" heading and the next "##" heading in
// docs/final-l5-05/FINAL_L5_05AI_ROUTE_ACTION_COVERAGE_REGISTRY.md -- not a
// hand-copied duplicate of the registry's row count.
const fs = require("fs");
const path = require("path");

const REGISTRY_PATH = path.join(__dirname, "..", "docs", "final-l5-05", "FINAL_L5_05AI_ROUTE_ACTION_COVERAGE_REGISTRY.md");
// FINAL-L5-05AM: corrected from the previously-reported 28 -- mechanical
// parsing (this guard) found the true row count is 29. FINAL-L5-05AK's
// prose undercounted its own "10 new actions" claim by one (the
// User suspend/unsuspend/deactivate/reactivate row covers 4 actions in 1
// row, and Customer session revoke-all was an 11th row, not folded into
// the stated 10) -- carried forward verbatim into FINAL-L5-05AL's "19->28"
// framing without ever being mechanically re-verified until now.
const EXPECTED_ACTION_COUNT = 29;
const REQUIRED_COLUMNS = ["Action", "Endpoint", "Permission", "Allowed roles", "Chromium coverage", "Source"];

function fail(reason) {
  console.log(JSON.stringify({ result: "ACTION_REGISTRY_GUARD_FAILED", reason }, null, 2));
  process.exit(1);
}

function main() {
  if (!fs.existsSync(REGISTRY_PATH)) fail(`registry file not found: ${REGISTRY_PATH}`);
  const text = fs.readFileSync(REGISTRY_PATH, "utf8");
  const lines = text.split(/\r?\n/);

  const headingIdx = lines.findIndex(l => l.trim() === "## High-risk action registry (partial — real endpoints, not fabricated)");
  if (headingIdx === -1) fail("could not locate '## High-risk action registry' heading");

  let endIdx = lines.length;
  for (let i = headingIdx + 1; i < lines.length; i++) {
    if (lines[i].trim().startsWith("## ") && i !== headingIdx) { endIdx = i; break; }
  }
  const section = lines.slice(headingIdx, endIdx);

  const tableHeaderIdx = section.findIndex(l => l.trim().startsWith("| Action") && l.includes("Endpoint"));
  if (tableHeaderIdx === -1) fail("could not locate action-table header row");
  const headerCols = section[tableHeaderIdx].split("|").map(c => c.trim()).filter(Boolean);
  for (const col of REQUIRED_COLUMNS) {
    if (!headerCols.some(h => h.toLowerCase() === col.toLowerCase())) {
      fail(`registry table missing required column: ${col}`);
    }
  }

  // Row lines: start with "|", are not the header, not the separator ("|---|...").
  const rows = [];
  for (let i = tableHeaderIdx + 1; i < section.length; i++) {
    const l = section[i].trim();
    if (!l.startsWith("|")) break; // table ends at first non-table line
    if (/^\|[\s-]+\|/.test(l)) continue; // markdown separator row
    rows.push(l);
  }

  const missingFields = [];
  rows.forEach((row, idx) => {
    const cells = row.split("|").map(c => c.trim()).filter((c, i, arr) => !(i === 0 && c === "") && !(i === arr.length - 1 && c === ""));
    if (cells.length < REQUIRED_COLUMNS.length) {
      missingFields.push({ row: idx + 1, reason: `expected ${REQUIRED_COLUMNS.length} columns, found ${cells.length}`, text: row.slice(0, 80) });
      return;
    }
    cells.forEach((cell, colIdx) => {
      if (!cell || cell === "—" || cell.length === 0) {
        missingFields.push({ row: idx + 1, column: REQUIRED_COLUMNS[colIdx] ?? `col${colIdx}`, reason: "empty cell" });
      }
    });
  });

  const result = {
    registry_path: path.relative(path.join(__dirname, ".."), REGISTRY_PATH),
    expected_action_count: EXPECTED_ACTION_COUNT,
    actual_action_count: rows.length,
    required_columns: REQUIRED_COLUMNS,
    missing_field_count: missingFields.length,
    missing_fields: missingFields.slice(0, 20),
  };

  if (rows.length !== EXPECTED_ACTION_COUNT) {
    result.result = "ACTION_REGISTRY_GUARD_FAILED";
    result.reason = `expected ${EXPECTED_ACTION_COUNT} action rows, found ${rows.length}`;
    console.log(JSON.stringify(result, null, 2));
    process.exit(1);
  }
  if (missingFields.length > 0) {
    result.result = "ACTION_REGISTRY_GUARD_FAILED";
    result.reason = "one or more rows have empty required fields";
    console.log(JSON.stringify(result, null, 2));
    process.exit(1);
  }

  result.result = "ACTION_REGISTRY_GUARD_PASSED";
  console.log(JSON.stringify(result, null, 2));
  process.exit(0);
}

main();

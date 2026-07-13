"""
MODULE-L5-01B: mechanical, targeted fix applier for admin_router_auth_guard
findings. Handles both severities:

- BARE_AUTHENTICATION_ONLY: replaces Depends(get_current_user) with
  Depends(require_super_admin) for the specific flagged handler.
- MISSING_AUTHENTICATION: the handler has NO auth dependency at all; inserts
  a new `u: UserContext = Depends(require_super_admin)` parameter into its
  signature (targeted by exact line number from the guard, not a blind
  file-wide replace).

Ensures require_super_admin and UserContext are imported in every touched
file.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def ensure_imports(text: str) -> str:
    m = re.search(r"from app\.dependencies\.auth import ([^\n]+)", text)
    if not m:
        # No existing import from this module -- add one after the last
        # top-level import block (first blank line after imports).
        lines = text.split("\n")
        insert_at = 0
        for i, l in enumerate(lines):
            if l.startswith("from ") or l.startswith("import "):
                insert_at = i + 1
        lines.insert(insert_at, "from app.dependencies.auth import require_super_admin, UserContext")
        return "\n".join(lines)
    imports_line = m.group(0)
    needed = []
    if "require_super_admin" not in imports_line:
        needed.append("require_super_admin")
    if "UserContext" not in imports_line:
        needed.append("UserContext")
    if not needed:
        return text
    new_line = imports_line.rstrip() + ", " + ", ".join(needed)
    return text.replace(imports_line, new_line, 1)


def fix_bare_auth(lines: list[str], line_no: int) -> bool:
    idx = line_no - 1
    for offset in range(0, 20):
        j = idx + offset
        if j >= len(lines):
            break
        if "Depends(get_current_user)" in lines[j]:
            lines[j] = lines[j].replace("Depends(get_current_user)", "Depends(require_super_admin)", 1)
            return True
    return False


def fix_missing_auth(lines: list[str], line_no: int) -> bool:
    """Insert a new auth parameter into the handler signature. Finds the
    line ending the decorator's own parens (the @router.get(...) call may
    span multiple lines) and then the `async def NAME(` opening, inserting
    a new parameter right after the opening paren or after `r: Request,`
    if present, to keep FastAPI's non-default-before-default ordering
    valid (Request has no default, so it is safe to insert immediately
    after)."""
    idx = line_no - 1
    # Find the "async def" line within a bounded window after the decorator.
    def_idx = None
    for offset in range(0, 10):
        j = idx + offset
        if j >= len(lines):
            break
        if re.search(r"^\s*async def \w+\(", lines[j]):
            def_idx = j
            break
    if def_idx is None:
        return False

    # Find where the signature's parameter list ends (the matching close-paren line).
    depth = 0
    end_idx = None
    for j in range(def_idx, min(def_idx + 25, len(lines))):
        depth += lines[j].count("(") - lines[j].count(")")
        if depth == 0 and j > def_idx:
            end_idx = j
            break
        if depth == 0 and "(" in lines[j] and ")" in lines[j] and j == def_idx:
            end_idx = j
            break
    if end_idx is None:
        return False

    indent_match = re.match(r"^(\s*)", lines[def_idx])
    indent = indent_match.group(1) + "    "
    new_param = f"{indent}u: UserContext = Depends(require_super_admin),"

    if end_idx == def_idx:
        # Single-line signature: "async def name(r: Request): -> insert before final ):"
        line = lines[def_idx]
        m = re.match(r"^(.*\()(.*)\)(.*):(.*)$", line)
        if not m:
            return False
        prefix, params, _, rest = m.groups()
        new_params = params.rstrip()
        if new_params and not new_params.endswith(","):
            new_params += ", "
        elif new_params:
            new_params += " "
        lines[def_idx] = f"{prefix}{new_params}u: UserContext = Depends(require_super_admin)){rest}:{rest and rest or ''}"
        # Simplify: rebuild cleanly.
        lines[def_idx] = re.sub(r"\)\s*:\s*$", f", u: UserContext = Depends(require_super_admin)):", line.rstrip())
        return True
    else:
        # Multi-line signature: insert a new parameter line just before the closing line.
        lines.insert(end_idx, new_param)
        return True


def fix_file(rel_path: str, findings: list[dict]) -> tuple[int, int]:
    path = ROOT / rel_path
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    fixed_bare = 0
    fixed_missing = 0

    # Process bottom-up so line-number inserts don't shift earlier findings.
    for f in sorted(findings, key=lambda x: -x["line"]):
        if f["severity"] == "BARE_AUTHENTICATION_ONLY":
            if fix_bare_auth(lines, f["line"]):
                fixed_bare += 1
        else:
            if fix_missing_auth(lines, f["line"]):
                fixed_missing += 1

    text = "\n".join(lines)
    text = ensure_imports(text)
    path.write_text(text, encoding="utf-8")
    return fixed_bare, fixed_missing


def main():
    findings_path = ROOT / "guard_findings2.json"
    data = json.loads(findings_path.read_text(encoding="utf-8"))
    findings = data["privileged_bare_auth_findings"]

    by_file: dict[str, list[dict]] = {}
    for f in findings:
        by_file.setdefault(f["file"], []).append(f)

    total_bare = total_missing = total = 0
    for rel_path, file_findings in by_file.items():
        b, m = fix_file(rel_path, file_findings)
        total_bare += b
        total_missing += m
        total += len(file_findings)
        print(f"{rel_path}: bare={b} missing={m} / total={len(file_findings)}")

    print(f"TOTAL: bare_fixed={total_bare} missing_fixed={total_missing} / {total} findings across {len(by_file)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())

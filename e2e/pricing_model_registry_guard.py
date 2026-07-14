"""
MODULE-L5-03: pricing-model registry guard (fail-closed).

Ensures the canonical pricing-model set has ONE source of truth and cannot drift:
  * VALID_PRICING_MODELS is derived from PRICING_MODEL_REGISTRY (identical sets);
  * every registry model has a label + non-empty required_fields;
  * _validate_pricing_config handles exactly the registry's models (no model is
    validated that isn't advertised, and none advertised that isn't validated);
  * the GET /v1/admin/pricing-models endpoint exists to serve the registry so
    clients need not hardcode the list.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
SVC = ROOT / "app" / "engines" / "admin_catalog" / "service.py"
ADMIN_ROUTER = ROOT / "app" / "engines" / "admin_catalog" / "admin_router.py"


def check() -> list[str]:
    findings = []
    from app.engines.admin_catalog.service import PRICING_MODEL_REGISTRY, VALID_PRICING_MODELS

    if set(VALID_PRICING_MODELS) != set(PRICING_MODEL_REGISTRY):
        findings.append(f"VALID_PRICING_MODELS {set(VALID_PRICING_MODELS)} != registry "
                        f"{set(PRICING_MODEL_REGISTRY)} (drift)")

    for code, meta in PRICING_MODEL_REGISTRY.items():
        if not meta.get("label"):
            findings.append(f"pricing model '{code}' missing label")
        if not meta.get("required_fields"):
            findings.append(f"pricing model '{code}' missing required_fields")

    # _validate_pricing_config must branch on exactly the registry's models.
    svc_text = SVC.read_text(encoding="utf-8")
    m = re.search(r'def _validate_pricing_config.*?(?=\ndef |\nclass |\n    async def )', svc_text, re.S)
    body = m.group(0) if m else ""
    validated = set(re.findall(r'model == "([a-z_]+)"', body))
    if validated and validated != set(PRICING_MODEL_REGISTRY):
        findings.append(f"_validate_pricing_config handles {validated}, registry is "
                        f"{set(PRICING_MODEL_REGISTRY)} (mismatch)")

    if '"/pricing-models"' not in ADMIN_ROUTER.read_text(encoding="utf-8"):
        findings.append("GET /v1/admin/pricing-models endpoint missing (clients would hardcode)")
    return findings


def main() -> int:
    findings = check()
    out = {
        "pricing_model_registry_findings": findings,
        "result": "PRICING_MODEL_REGISTRY_GUARD_FAILED" if findings else "PRICING_MODEL_REGISTRY_GUARD_PASSED",
    }
    print(__import__("json").dumps(out, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())

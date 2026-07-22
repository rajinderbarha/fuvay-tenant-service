# Known Limitations

- `app/engines/field_ops/service.py`'s invoice-generation call site is
  wrapped in a pre-existing `try/except Exception as e: logger.warning(...)`
  block (unrelated to this slice) that would silently swallow a
  `PERMISSION_DENIED` from `DocumentService.generate_document` if the
  tenant context were ever wrong. This slice's fix makes the tenant match
  trivially true (`job.tenant_id` passed as both actor and target), so it
  is not a live bug, but the swallow pattern itself is not remediated —
  out of scope (service-layer error-handling refactor, not an
  authorization boundary).
- `readonly@demo-ac-services.local` intentionally untouched, per mission
  PRESERVE list.
- Migration 144 remains unapplied, per mission OUT-OF-SCOPE list.
- N01 domain-integrity backlog unchanged, per mission OUT-OF-SCOPE list.

# Intelligence KB `allowed_roles_json` — Conclusive Disposition

## Investigation (exhaustive this slice — searched the entire `app/` tree, not just `kb_service.py`)

```
grep -rn "allowed_roles" app/ --include=*.py
```
Exactly 4 matches, all in 2 files:
1. `app/engines/analytics/intelligence_models.py:44` — model column definition: `allowed_roles_json: Mapped[list] = mapped_column(JSONB, default=list)`.
2. `app/engines/analytics/intelligence_models.py:94` — `to_dict()` serialization: `"allowed_roles_json": self.allowed_roles_json or []`.
3. `app/engines/analytics/kb_service.py:202` — write path on create: `allowed_roles_json=payload.get("allowed_roles_json", [])`.
4. `app/engines/analytics/kb_service.py:248` — included in the updatable-fields whitelist for edits.

**Zero matches anywhere else** — no retrieval/query method, no RAG search filter, no content-serving endpoint, no permission-check code path reads this field back. Confirmed by grepping the entire backend, not a targeted single-file check.

## Per-question findings

| Question | Answer |
|---|---|
| Where is it written? | `kb_service.py` create/update, from the admin UI's multi-select |
| Where is it read? | Only `to_dict()` — for display back to the admin UI, nowhere else |
| Does it affect retrieval? | No — no RAG/search/query code path consults it |
| Does it affect UI visibility? | No — nothing outside the admin KB-management page itself reads or filters on it |
| Does it affect authorization? | No |
| Is it response-only? | Yes — its only observable effect is round-tripping through the API (write → stored → read back in the same admin UI) |
| Do existing records rely on it? | Records store whatever list was set, but nothing downstream depends on that value being correct or even present |
| Do tests assert behavior? | Not investigated for a dedicated test this slice — grepped for `allowed_roles` in `tests/` and found no matches, consistent with no behavior existing to test |
| Does it represent intended future functionality? | Very likely, based on its name and multi-select UI design — this looks like a scaffolded access-control feature that was never wired to actual enforcement, not an accidental leftover |

## Disposition: **DISPLAY_ONLY**

This is a factual description of current behavior, not a euphemism: the field is stored and shown back to the admin who set it, and does nothing else. It is **not** turned into `ENFORCE_AS_AUTHORIZATION` merely because it is named `allowed_roles` — doing so would be exactly the kind of naming-based inference this slice series has repeatedly been warned against. It is also not `ENFORCE_AS_CONTENT_TARGETING`, because no content-targeting/filtering code path exists either — there's no query-time distinction of *any* kind based on this field, RBAC or otherwise.

## Non-blocking recommendation (not executed this slice)
Per the brief, this decision does not block user remediation and required only documentation. For a future slice: either (a) wire real enforcement at whatever the actual KB-retrieval/query code path is (would need its own investigation to locate, since it wasn't found in this search — possibly not yet built), or (b) remove the field and its UI to stop presenting an access control that doesn't function, since a security-shaped UI control with no effect is a worse outcome than no control at all (an admin configuring it reasonably believes it works).

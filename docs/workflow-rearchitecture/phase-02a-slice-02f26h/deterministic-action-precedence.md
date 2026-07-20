# Deterministic Action Precedence — Slice 2F-26H

1. Explicit route-specific override
2. Established service/state-machine operation
3. Qualified service-method verb (leading verb)
4. Endpoint function verb (leading verb)
5. Tokenized path verb (trailing segment)
6. Strong HTTP fallback: DELETE→delete; PUT/PATCH **with proven write**→update
7. `REQUIRES_MANUAL_ACTION_ADJUDICATION`

GET carries `other` (a read is not a mutation action). **POST never defaults to
create** — a POST without reliable action evidence returns manual adjudication.
Within the strongest available level, two sources that map to different actions
fail closed (see `action-conflict-report.md`).

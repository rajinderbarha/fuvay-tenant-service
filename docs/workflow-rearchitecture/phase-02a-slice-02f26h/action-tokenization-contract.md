# Action Tokenization Contract — Slice 2F-26H

Tokenize path, endpoint function name and qualified service-method names by
splitting on `/`, `-`, `_`, `.` and CamelCase boundaries, lowercasing, and
dropping path parameters (`{tenant_id}`).

| Input | Tokens |
|---|---|
| `bulk-disable` | bulk, disable |
| `mark-all-read` | mark, all, read |
| `terminate_confirm` | terminate, confirm |
| `rotateApiKey` | rotate, api, key |
| `resend-invite` | resend, invite |

Excluded from verb consideration: path parameter names, noun stopwords
(`NOUN_STOPWORDS`), docstrings/comments (never read — only names and paths),
and request-field values. Function/method names use the **leading** meaningful
token (verb-first naming); REST paths use the **trailing** verb segment.

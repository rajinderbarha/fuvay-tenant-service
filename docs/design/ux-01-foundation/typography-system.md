# Typography System

Font families: Inter (base, already loaded via Google Fonts in super-admin's
`globals.css`) and JetBrains Mono (numeric/code). `theme.css` defines
`--font-family-base`/`--font-family-mono` so components never hardcode a
family string.

## Scale (`tokens/typography.ts` → `.ds-text-*` classes)
| Token | Size | Weight | Line height | Use |
|---|---|---|---|---|
| display | 2.25rem | 700 | 2.75rem | rare hero numbers |
| pageTitle | 1.5rem | 700 | 2rem | `PageHeader` title |
| sectionTitle | 1.125rem | 600 | 1.5rem | `Section`/`Card` group titles |
| cardTitle | 1rem | 600 | 1.375rem | `Card` header |
| body | 0.9375rem | 400 | 1.5rem | default paragraph |
| bodyCompact | 0.8125rem | 400 | 1.25rem | dense UI text |
| label | 0.8125rem | 500 | 1.125rem | form field labels |
| helper | 0.75rem | 400 | 1rem | field descriptions/errors |
| caption | 0.6875rem | 500 | 0.875rem | metadata, timestamps |
| badge | 0.6875rem | 600 | 1rem | `StatusBadge` text |
| tableHeader | 0.6875rem | 600 | 1rem | uppercase, tracked |
| tableCell | 0.875rem | 400 | 1.25rem | `DataTable` cells |
| numeric | 0.9375rem | 600 | 1.25rem | mono, amounts/counts |
| code | 0.8125rem | 400 | 1.25rem | mono, code/IDs |

Components apply these via className (`ds-text-*`) rather than inline
font-size, so a future scale change is a one-file edit.

# CUSTOMER-L5-05 — Question Renderer Registry

`domain/question-renderer-registry.ts#resolveQuestionRenderer(questionType)`
is the single, centralized, typed lookup — mirroring CUSTOMER-L5-03's
`module-registry.ts` pattern. It never resolves a component from a
backend-supplied string (there is no backend `question_type` field to
resolve in the first place — see contract-matrix.md); it exists for
forward-compatibility, so a future step type added to the domain model
without a matching renderer fails closed (`unsupported_question_received`
logged, customer sees a safe "this step isn't available yet" state) instead
of crashing.

## SINGLE_SELECT

| | |
|---|---|
| Backend schema | Real per-option data (issue types, brands, service types); no backend "question" wrapper exists |
| Client schema | `SingleSelectOption { id, label, description? }` (`components/SingleSelectRenderer.tsx`) |
| Answer schema | `canonicalAnswer: string` (the option's stable backend ID) |
| Renderer | `SingleSelectRenderer` — `AppRadio` per option, immediate-submit on tap (no separate continue) |
| Validation | Implicit — only a real option from the fetched list can be tapped |
| Normalization | `normalizeSingleSelectAnswer` |
| Accessibility | `accessibilityRole="radiogroup"` container, each option `accessibilityRole="radio"` with `selected`/`disabled` state |
| Localization | Options' `label`/`description` come straight from the backend's `name` field — not independently translated, since the backend has no locale variants (see known-gaps) |
| Test coverage | `assistant-session.test.ts` (submission/branching), `answer-normalization.test.ts` |

Used for: `issue_type`, `brand`, `service_type`.

## MULTI_SELECT

| | |
|---|---|
| Backend schema | Real service-option data (`is_customer_selectable` items only) |
| Client schema | `MultiSelectOption { id, label }` |
| Answer schema | `canonicalAnswer: string[]` — order preserved from the backend's own order, never re-sorted |
| Renderer | `MultiSelectRenderer` — `AppCheckbox` per option, explicit "Continue" action |
| Validation | None enforced client-side beyond selection toggling — no real min/max-selection field exists on `MasterServiceOption` to validate against (see known-gaps) |
| Normalization | `normalizeMultiSelectAnswer` — joins labels for the summary, or "None selected" if empty |
| Accessibility | Each option `accessibilityRole="checkbox"` with `checked`/`disabled` state |
| Test coverage | `answer-normalization.test.ts`, `assistant-session.test.ts` |

Used for: `service_option`.

## SHORT_TEXT

| | |
|---|---|
| Backend schema | No backend field constrains this — client-defined free text tied to a real trigger (`requires_description` on an issue type, or `requires_customer_notes` on the offering) |
| Client schema | Plain string, max 500 characters |
| Answer schema | `canonicalAnswer: string` — trimmed, whitespace-collapsed, control characters stripped |
| Renderer | `ShortTextRenderer` — `AppTextArea` with character count, explicit "Continue" |
| Validation | Required variant (`issue_description`) blocks continue until non-empty after trim; optional variant (`customer_note`) never blocks |
| Normalization | `normalizeShortTextAnswer` |
| Accessibility | Standard `AppTextField` labelling (already accessible — reused unmodified) |
| Localization | The prompt/helper text is fully translated (`assistant.issueDescriptionTitle`/`customerNoteTitle` etc., en/hi/pa); the customer's own typed answer is never translated, matching CUSTOMER-L5-05 §55's "canonical answer values remain language independent" |
| Test coverage | `answer-normalization.test.ts` (trim, control-char strip, length cap, Hindi/Punjabi preservation) |

Used for: `issue_description`, `customer_note`.

## INFORMATION

| | |
|---|---|
| Backend schema | Real trigger (`requires_photo` on an issue type, or `requires_photo_upload` on the offering); no backend copy field — the explanation text is app-authored, approved product copy, translated |
| Client schema | None — no answer is actually collected |
| Answer schema | `canonicalAnswer: "acknowledged"` — a fixed sentinel, never a customer-authored value |
| Renderer | `InformationRenderer` — heading + body + explicit "Continue" |
| Validation | None — acknowledgement only |
| Normalization | `normalizeInformationAcknowledgement` |
| Accessibility | Real heading (`accessibilityRole="header"`) |
| Test coverage | `answer-normalization.test.ts` |

Used for: `photo_boundary` (the CUSTOMER-L5-05 §27 media-request boundary —
explains that a photo will be requested in a later, not-yet-built step;
never implements upload itself).

## Not Implemented — No Real Trigger Exists

`BOOLEAN`, `NUMBER`, `LONG_TEXT`, `DATE`, `TIME` question types have no
backing data anywhere in the catalog (see contract-matrix.md) — building
renderers for them would mean inventing the questions themselves, which
this sprint does not do.

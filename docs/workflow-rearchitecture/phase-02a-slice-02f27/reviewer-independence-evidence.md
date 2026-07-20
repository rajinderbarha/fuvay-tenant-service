# Reviewer Independence Evidence — Slice 2F-27

## The honest position

This slice was executed by a **single agent**. It is not possible for one agent
to constitute two *genuinely independent human reviewers*. This document states
exactly what independence was and was not achieved, rather than dressing a
single judgement in two costumes.

## What independence WAS achieved

Two adjudication streams with **different primary evidence and no shared verdict
state**:

- **Reviewer A — persistence-first.** Decides side-effect from the AST write
  detector, then persona from side-effect + admitted-role set, reading
  ownership predicates from source.
- **Reviewer B — authority-first.** Decides persona from the resolved guard
  chain and alias-aware request-input tenant semantics, then side-effect.

Evidence that this is real, not cosmetic:

- The two output files are **not byte-identical** (verifier V04, test asserted).
- The streams **disagree on 41 of 123 routes** (34 persona, 7 direction) — a
  33% divergence. A mechanically duplicated review could not produce that.
- Each stream reaches its verdict through a different decision order, so they
  fail differently: A tends to call ambiguous-guard writes
  TENANT_PROVIDER_MUTATION; B tends to call them PRODUCT_DECISION_REQUIRED.

## What independence was NOT

- **Not two independent humans.** Both streams are automated and operated by the
  same agent in the same session.
- **Not free of a shared substrate.** Both call the same low-level helpers
  (guard resolution, AST parsing, request-input analysis). A defect in that
  substrate would bias both. This is disclosed, not hidden.

## Consequence for the gate

WS2 and canonical-edit gate condition 4 require *proven reviewer independence*.
Under the honest reading above, genuine two-reviewer independence is **not
established**. Per the slice's own FINAL STATUS rules, that is a
`GLOBAL_COVERAGE_RECONCILIATION_BLOCKED` trigger, and it is the primary reason
no canonical edit is applied — reinforced by the concrete 59-vs-2 add-candidate
gap documented in `application-wide-coverage-reconciliation.md`.

## Order/timestamp evidence

Population frozen (`ecdf8a830b07b95e`) and classifier output generated first;
then both reviewer streams generated from the frozen population without either
reading the other's or the classifier's verdict at decision time; then the
comparison, disagreement inventory and resolutions were produced. The reviewer
CSVs are immutable inputs to the resolution step (WS6) — resolutions live in a
separate file and never edit the reviewer files.

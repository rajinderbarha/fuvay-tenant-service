# Localization Readiness Report

No i18n framework is wired into `frontend/super-admin` today (confirmed by absence of any
`i18next`/`next-intl`/similar dependency in `package.json` and absence of any translation-key
usage in the existing `app/admin/**` routes reviewed). UX-02 does not add one — that is a larger,
separate product decision (see `product-decisions-required.md`).

## What UX-02 does do
- All new UX-02 components use `overflowWrap`/flexible layout (no fixed-width text containers)
  so that longer translated strings do not clip — demonstrated in the "Long / translated text"
  section of `/dev/ux-02/states`.
- No string concatenation that would break word order for other languages (e.g. status labels are
  rendered as standalone `StatusBadge` components, not interpolated into a sentence).
- All new user-facing strings are plain English literals inline in components/fixtures — not yet
  extracted into a translation-key file, since no i18n system exists to consume one.

## Gap
If i18n is adopted platform-wide, all UX-02 strings will need extraction into whatever key format
is chosen. Not done in this phase — tracked in `deferred-items.md`.

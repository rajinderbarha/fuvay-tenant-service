# Localization Readiness Report

No i18n library is wired this phase — all strings are inline English
literals, matching UX-01/UX-02 precedent. Currency is hardcoded to `₹`
(Indian Rupee) in finance-related showcase pages, matching the fixture
data's home_services/India-oriented examples — this is a placeholder, not
a locale-aware formatter. Long-localized-text rendering was not separately
tested (see deferred-items.md); flex-wrap layouts used throughout should
tolerate longer strings reasonably well but this is not verified.

"""Legal Documents — the published text of Terms, Privacy and friends.

Why this engine exists
----------------------
Before it, the Terms of Service and Privacy Notice existed ONLY as hardcoded
JSX in ``frontend/tenant-portal/app/terms/page.tsx`` and ``.../privacy/page.tsx``.
That had three consequences worth stating plainly:

* Publishing a policy change required a frontend code deploy.
* No other surface could show them. The customer mobile app reads
  ``EXPO_PUBLIC_TERMS_URL`` / ``EXPO_PUBLIC_PRIVACY_URL``, which are unset, so
  its legal links silently do nothing; ``ProfileScreen`` hardcodes both to
  ``null`` and the rows are omitted entirely.
* Nothing recorded WHICH text a user agreed to. Tenant signup does write a
  ``consent_records`` row (consent_type ``tos_privacy``), but the
  ``policy_version`` it stamps comes from ``dpdp_policy_versions`` — the
  data-protection PROCESS policy (SLA phases, request types), not the Terms
  the person actually read. The ledger could not answer "what did they see?".

This engine stores the documents themselves, versioned, and lets signup stamp
the exact version that was live at the moment of acceptance.

What it deliberately does NOT do
--------------------------------
It does not introduce a second acceptance ledger. ``consent_records`` is
already the immutable consent ledger (one row per grant/withdraw, never
updated) and it already carries ip/user_agent/source. Acceptance keeps living
there; this engine only supplies the document identity that goes into it.
"""
from __future__ import annotations

ENGINE_ID = "legal_documents"

# ── Document types ───────────────────────────────────────────────────────────
# A closed set. A new legal document is a new constant here plus a row, never
# a free-text slug from a client — the public route takes doc_type straight
# from the URL and an open set would let anyone probe for arbitrary rows.
DOC_TERMS_OF_SERVICE = "terms_of_service"
DOC_PRIVACY_POLICY = "privacy_policy"
DOC_REFUND_POLICY = "refund_policy"
DOC_COOKIE_POLICY = "cookie_policy"
DOC_ACCEPTABLE_USE = "acceptable_use"

VALID_DOC_TYPES: dict[str, str] = {
    DOC_TERMS_OF_SERVICE: "Terms of Service",
    DOC_PRIVACY_POLICY: "Privacy Policy",
    DOC_REFUND_POLICY: "Refund & Cancellation Policy",
    DOC_COOKIE_POLICY: "Cookie Policy",
    DOC_ACCEPTABLE_USE: "Acceptable Use Policy",
}

#: The documents a signup consent must reference. Kept separate from
#: VALID_DOC_TYPES so adding, say, a cookie policy does not silently start
#: blocking signup when no version of it has been published yet.
SIGNUP_CONSENT_DOC_TYPES = (DOC_TERMS_OF_SERVICE, DOC_PRIVACY_POLICY)

# ── Audiences ────────────────────────────────────────────────────────────────
# One document type can have a different text per audience: the tenant Terms
# govern a business workspace, the customer Terms govern booking a service.
# `all` is the fallback used when no audience-specific version is published.
AUDIENCE_ALL = "all"
AUDIENCE_TENANT = "tenant"
AUDIENCE_CUSTOMER = "customer"
AUDIENCE_PROVIDER = "provider"

VALID_AUDIENCES = {AUDIENCE_ALL, AUDIENCE_TENANT, AUDIENCE_CUSTOMER, AUDIENCE_PROVIDER}

# ── Lifecycle ────────────────────────────────────────────────────────────────
# draft     — editable, never served publicly
# published — immutable, served once effective_at has passed
# archived  — superseded; still readable by id so an old consent record can be
#             resolved back to the exact text that was accepted
STATUS_DRAFT = "draft"
STATUS_PUBLISHED = "published"
STATUS_ARCHIVED = "archived"

VALID_STATUSES = {STATUS_DRAFT, STATUS_PUBLISHED, STATUS_ARCHIVED}

DEFAULT_LOCALE = "en"

#: Body format. Markdown is stored, never HTML: the body is rendered by four
#: different clients (Next.js web, two React Native apps, email) and shipping
#: raw HTML to a WebView-less mobile renderer would mean either an HTML parser
#: on every client or an XSS-shaped hole on the web one.
BODY_FORMAT_MARKDOWN = "markdown"

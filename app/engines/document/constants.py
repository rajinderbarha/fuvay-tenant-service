"""Document Engine — constants. Proven Level 5."""
class DocType:
    SERVICE_AGREEMENT = "service_agreement"
    WARRANTY          = "warranty"
    COMPLETION_CERT   = "completion_certificate"
    GST_INVOICE       = "gst_invoice"
    INSPECTION_REPORT = "inspection_report"
    CUSTOM            = "custom"

class DocStatus:
    DRAFT   = "draft"
    SENT    = "sent"
    VIEWED  = "viewed"
    SIGNED  = "signed"
    EXPIRED = "expired"
    VOIDED  = "voided"

class DocEventType:
    GENERATED = "generated"
    SENT      = "sent"
    VIEWED    = "viewed"
    SIGNED    = "signed"
    EXPIRED   = "expired"
    VOIDED    = "voided"

TERMINAL_DOC_STATUSES = [DocStatus.SIGNED, DocStatus.EXPIRED, DocStatus.VOIDED]
SIGNING_URL_TTL_HOURS = 24

# Sequential document numbers — Redis INCR (atomic, no gaps)
REDIS_DOC_COUNTER    = "serviceos:doc:counter:{tenant_id}"
REDIS_SIGNING_URL    = "serviceos:doc:sign_url:{token}"

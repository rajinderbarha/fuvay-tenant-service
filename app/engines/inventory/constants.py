"""Inventory Engine — constants. Proven Level 5."""
class StockTxnType:
    RECEIPT         = "receipt"
    RESERVATION     = "reservation"
    CONFIRMATION    = "confirmation"   # reservation confirmed on job close
    DEPLETION       = "depletion"      # direct consumption without reservation
    RETURN          = "return"
    ADJUSTMENT      = "adjustment"     # cycle count correction
    TRANSFER        = "transfer"       # warehouse → van
    REPLENISHMENT   = "replenishment"  # auto-generated request

class LocationType:
    WAREHOUSE = "warehouse"
    VAN       = "van"
    SITE      = "site"

class ReservationStatus:
    ACTIVE     = "active"
    CONFIRMED  = "confirmed"
    RELEASED   = "released"
    EXPIRED    = "expired"

# Redis keys — SELECT FOR UPDATE pattern in service layer
REDIS_STOCK_BALANCE  = "serviceos:inv:balance:{item_id}:{location_id}"
REDIS_STOCK_LOCK     = "serviceos:inv:lock:{item_id}:{location_id}"
RESERVATION_TTL_HOURS = 48   # same as credit reservation
LOW_STOCK_ALERT_PCT  = 0.20  # alert when stock < 20% of min level

class ItemStatus:
    """Draft/publish lifecycle for the inventory_document_extraction plugin
    engine. Existing/legacy items are 'published' (migration 145 default)."""
    DRAFT     = "draft"
    PUBLISHED = "published"

DOCUMENT_EXTRACTION_ENGINE_ID = "inventory_document_extraction"
MAX_UPLOAD_PDF_BYTES = 15 * 1024 * 1024  # 15MB

# ── Error codes ────────────────────────────────────────────────────
ERR_ENGINE_DISABLED   = "INVENTORY_EXTRACTION_ENGINE_DISABLED"
ERR_PDF_UNREADABLE    = "INVENTORY_EXTRACTION_PDF_UNREADABLE"
ERR_LLM_BAD_RESPONSE  = "INVENTORY_EXTRACTION_LLM_BAD_RESPONSE"
ERR_NOT_DRAFT         = "INVENTORY_ITEM_NOT_DRAFT"

EXTRACTION_SYSTEM_PROMPT = """You are an inventory data-extraction assistant for a home-services provider platform.
You will be given raw text extracted from a PDF (a price list, stock sheet, or supplier catalogue).
Identify every distinct inventory/parts line item you can find and return STRICT JSON only — no prose,
no markdown fences — matching exactly this shape:

{"items": [
  {"name": "string (required)", "sku": "string or null", "quantity": number or null,
   "unit": "string or null (e.g. pcs, box, litre)", "unit_cost": number or null,
   "category": "string or null", "gst": "number or null (GST percent, e.g. 18)",
   "warranty": "string or null (e.g. '12 months')"}
]}

Rules:
- If a field is not present in the text, use null — never invent values.
- quantity and unit_cost must be plain numbers (no currency symbols, no commas).
- If you cannot confidently identify any line items, return {"items": []}.
- Output ONLY the JSON object, nothing else."""

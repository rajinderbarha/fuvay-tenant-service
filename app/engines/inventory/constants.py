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

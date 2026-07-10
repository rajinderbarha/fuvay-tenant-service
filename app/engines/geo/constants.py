"""Geo Engine — constants."""

class ZoneType:
    PINCODE  = "pincode"
    AREA     = "area_name"
    POLYGON  = "polygon"
    RADIUS   = "radius"

class StaffStatus:
    AVAILABLE   = "available"
    BUSY        = "busy"
    OFFLINE     = "offline"
    ON_LEAVE    = "on_leave"

# Earth radius km for Haversine
EARTH_RADIUS_KM    = 6371.0
ROAD_FACTOR        = 1.3          # straight-line × 1.3 ≈ road distance
DEFAULT_RADIUS_KM  = 10.0
MAX_RADIUS_KM      = 50.0
STAFF_LOC_TTL_SEC  = 600          # 10 min — stale after this

REDIS_STAFF_LOC    = "serviceos:geo:staff_loc:{tenant_id}"
REDIS_ZONE_PINS    = "serviceos:geo:zone_pins:{zone_id}"
REDIS_TENANT_ZONES = "serviceos:geo:tenant_zones:{tenant_id}"

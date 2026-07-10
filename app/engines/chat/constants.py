"""Chat Engine — constants. Proven Level 5.
Typing state: pure Redis, zero DB writes — proven by no self.db.add() in typing methods.
"""
class ConversationStatus:
    ACTIVE   = "active"
    ARCHIVED = "archived"
    CLOSED   = "closed"

class MessageType:
    TEXT      = "text"
    SYSTEM    = "system"
    MEDIA     = "media"
    TEMPLATE  = "template"

class ParticipantRole:
    CUSTOMER = "customer"
    STAFF    = "staff"
    TENANT   = "tenant"
    SYSTEM   = "system"

class EntityType:
    JOB    = "job"
    TENANT = "tenant"

# PROVEN: Typing state — Redis only, never touches Postgres
TYPING_TTL_SECONDS   = 5     # Key expires after 5s of silence
TYPING_PING_SECONDS  = 3     # Mobile app pings every 3s
REDIS_TYPING         = "serviceos:chat:typing:{conversation_id}:{user_id}"
REDIS_UNREAD         = "serviceos:chat:unread:{conversation_id}:{user_id}"
REDIS_CONV_LOCK      = "serviceos:chat:conv_lock:{entity_type}:{entity_id}"

MAX_MESSAGE_SIZE_CHARS = 4000
MAX_PARTICIPANTS       = 20

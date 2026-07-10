"""Appointment Engine — constants."""

class AS:
    AVAILABLE   = "available"
    HOLD        = "hold"
    CONFIRMED   = "confirmed"
    REMINDED    = "reminded"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    NO_SHOW     = "no_show"
    CANCELLED   = "cancelled"
    RESCHEDULED = "rescheduled"

APPOINTMENT_TRANSITIONS: dict[str, list[str]] = {
    AS.AVAILABLE:   [AS.HOLD],
    AS.HOLD:        [AS.CONFIRMED, AS.CANCELLED],
    AS.CONFIRMED:   [AS.REMINDED, AS.CANCELLED, AS.RESCHEDULED],
    AS.REMINDED:    [AS.IN_PROGRESS, AS.NO_SHOW, AS.CANCELLED],
    AS.IN_PROGRESS: [AS.COMPLETED, AS.NO_SHOW],
    AS.COMPLETED:   [],
    AS.NO_SHOW:     [],
    AS.CANCELLED:   [],
    AS.RESCHEDULED: [],
}

TERMINAL_APPT_STATUSES = [AS.COMPLETED, AS.NO_SHOW, AS.CANCELLED, AS.RESCHEDULED]

# Hold TTL — 10 minutes. Celery expires slot if not confirmed.
HOLD_TTL_SECONDS     = 600
HOLD_TTL_MINUTES     = 10

# Reminders: 24h and 2h before
REMINDER_HOURS       = [24, 2]

# No-show: 30 min past scheduled end
NO_SHOW_GRACE_MINUTES = 30

# Slot granularity
DEFAULT_SLOT_DURATION_MINUTES = 60
MIN_BUFFER_MINUTES            = 15

REDIS_SLOT_HOLD      = "serviceos:appt:hold:{staff_id}:{slot_dt}"
REDIS_APPT_CALENDAR  = "serviceos:appt:calendar:{staff_id}:{date}"

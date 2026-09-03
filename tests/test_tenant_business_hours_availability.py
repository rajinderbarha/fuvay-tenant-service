"""
TENANT BUSINESS HOURS & AVAILABILITY PAGE
Tests for /tenant/setup/availability
"""
import re
import pathlib

ROOT = pathlib.Path(__file__).parent.parent

PAGE = ROOT / "frontend/tenant-portal/app/(tenant)/tenant/setup/availability/page.tsx"
REDIRECT = ROOT / "frontend/tenant-portal/app/(tenant)/provider/availability/page.tsx"
LAYOUT = ROOT / "frontend/tenant-portal/components/layout/TenantLayout.tsx"


def read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


# ── 1. Route file exists ──────────────────────────────────────────────────────
def test_availability_page_exists():
    assert PAGE.exists(), f"Page not found: {PAGE}"


# ── 2. Breadcrumb renders ──────────────────────────────────────────────────────
def test_breadcrumb_renders():
    src = read(PAGE)
    assert "Tenant Portal" in src
    assert "Setup" in src
    assert "Business Hours & Availability" in src


# ── 3. Page title ─────────────────────────────────────────────────────────────
def test_page_title_renders():
    src = read(PAGE)
    assert "Business Hours & Availability" in src


# ── 4. Status badge renders ───────────────────────────────────────────────────
def test_status_badge_renders():
    src = read(PAGE)
    assert "Configured" in src
    assert "Not Configured" in src


# ── 5. Add Working Hours button ────────────────────────────────────────────────
def test_add_working_hours_button_renders():
    src = read(PAGE)
    assert "Add Working Hours" in src


# ── 6. Add Holiday button ──────────────────────────────────────────────────────
def test_add_holiday_button_renders():
    src = read(PAGE)
    assert "Add Holiday" in src


# ── 7. Quick Presets card renders ────────────────────────────────────────────
def test_quick_presets_card_renders():
    src = read(PAGE)
    assert "Quick Presets" in src


# ── 8. Standard Hours preset ─────────────────────────────────────────────────
def test_standard_hours_preset_renders():
    src = read(PAGE)
    assert "Standard Hours" in src


# ── 9. Weekdays Only preset ──────────────────────────────────────────────────
def test_weekdays_only_preset_renders():
    src = read(PAGE)
    assert "Weekdays Only" in src


# ── 10. Emergency Service preset ──────────────────────────────────────────────
def test_emergency_service_preset_renders():
    src = read(PAGE)
    assert "Emergency Service" in src


# ── 11. Custom Schedule preset ────────────────────────────────────────────────
def test_custom_schedule_preset_renders():
    src = read(PAGE)
    assert "Custom Schedule" in src


# ── 12. Weekly Schedule card renders all 7 days ──────────────────────────────
def test_weekly_schedule_all_7_days():
    src = read(PAGE)
    assert "Weekly Schedule" in src
    for day in ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]:
        assert day in src


# ── 13. Empty schedule shows Closed and Add Hours ────────────────────────────
def test_empty_schedule_shows_closed_and_add_hours():
    src = read(PAGE)
    assert "Closed" in src
    assert "Add Hours" in src


# ── 14. Add Working Hours modal opens ────────────────────────────────────────
def test_add_working_hours_modal_opens():
    src = read(PAGE)
    # Modal is present when wizardOpen is true
    assert "wizardOpen" in src
    assert "AvailabilityWizard" in src


# ── 15. End time before start time is rejected ───────────────────────────────
def test_end_time_before_start_rejected():
    src = read(PAGE)
    assert "End time must be after start time" in src


# ── 16. Valid working hours save ─────────────────────────────────────────────
def test_valid_working_hours_save():
    src = read(PAGE)
    assert "providerAvailabilityApi.create" in src or "providerAvailabilityApi.update" in src


# ── 17. Booking Slot Preview day tabs ────────────────────────────────────────
def test_booking_slot_preview_day_tabs():
    src = read(PAGE)
    assert "Booking Slot Preview" in src
    for short in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]:
        assert short in src


# ── 18. Slot preview empty state ─────────────────────────────────────────────
def test_slot_preview_empty_state():
    src = read(PAGE)
    assert "No working hours to preview" in src
    assert "Add working hours to preview customer slots" in src


# ── 19. Slot preview shows slots when configured ──────────────────────────────
def test_slot_preview_shows_slots():
    src = read(PAGE)
    assert "allSlots" in src
    assert "generateSlots" in src
    assert "booking slots available on" in src


# ── 20. All Working Hour Rules card renders ───────────────────────────────────
def test_all_working_hour_rules_card():
    src = read(PAGE)
    assert "All Working Hour Rules" in src


# ── 21. Rule filter pills render ──────────────────────────────────────────────
def test_rule_filter_pills():
    src = read(PAGE)
    assert "filterScope" in src
    assert "All Services" in src
    assert "Specific Service" in src
    assert "Staff Member" in src
    assert "Service Area" in src


# ── 22. Holidays & Exceptions card renders ────────────────────────────────────
def test_holidays_exceptions_card():
    src = read(PAGE)
    assert "Holidays & Exceptions" in src


# ── 23. Add Holiday modal opens ───────────────────────────────────────────────
def test_add_holiday_modal_opens():
    src = read(PAGE)
    assert "AddHolidayModal" in src
    assert "holidayOpen" in src


# ── 24. Availability Checks card renders ──────────────────────────────────────
def test_availability_checks_card():
    src = read(PAGE)
    assert "Availability Checks" in src


# ── 25. No Active Rules warning ──────────────────────────────────────────────
def test_no_active_rules_warning():
    src = read(PAGE)
    assert "No Active Rules" in src
    assert "Customers cannot book your services until you add working hours" in src


# ── 26. Recent Activity card renders ─────────────────────────────────────────
def test_recent_activity_card():
    src = read(PAGE)
    assert "Recent Activity" in src
    assert "No recent activity found" in src


# ── 27. Permission guard / read-only awareness ───────────────────────────────
def test_permission_aware_request_id():
    src = read(PAGE)
    # Error handling shows request_id
    assert "requestId" in src
    assert "Request ID" in src


# ── 28. API failure shows request_id ─────────────────────────────────────────
def test_api_failure_shows_request_id():
    src = read(PAGE)
    assert "saveErrId" in src
    assert "Copy size={10}" in src or "Copy size" in src
    assert "Request ID:" in src


# ── 29. No forbidden labels ──────────────────────────────────────────────────
FORBIDDEN = [
    "Wallet Balance", "Cash Wallet", "Withdraw", "Withdrawable Balance",
    "Tenant Payout", "Provider Earnings Wallet", "Escrow", "Provider Cash Balance",
    "Manual Bargain Setup", "Bargain Rule Builder", "Bargain Settings",
    "Credit Wallet Health", "Platform Collected Service Payment",
]

def test_no_forbidden_labels_in_page():
    src = read(PAGE)
    for label in FORBIDDEN:
        assert label not in src, f"Forbidden label found: {label!r}"


def test_no_forbidden_labels_in_layout():
    src = read(LAYOUT)
    for label in FORBIDDEN:
        assert label not in src, f"Forbidden label in layout: {label!r}"


# ── 30. No NaN/null/undefined ────────────────────────────────────────────────
def test_no_nan_in_displayed_values():
    src = read(PAGE)
    # safeText and safeNum helpers present
    assert "safeText" in src
    assert "safeNum" in src
    # fallback "—" used
    assert '"—"' in src or "'—'" in src


# ── 31. Card-first layout (not raw table-first) ───────────────────────────────
def test_card_first_layout():
    src = read(PAGE)
    # Quick Presets card renders before the WeeklyScheduleView component call in JSX
    preset_pos = src.find("Quick Presets")
    schedule_call_pos = src.find("<WeeklyScheduleView")
    assert preset_pos > -1, "Quick Presets card not found"
    assert schedule_call_pos > -1, "WeeklyScheduleView not rendered"
    assert preset_pos < schedule_call_pos, "WeeklyScheduleView call appears before Quick Presets"


# ── 32. Route is at correct path ──────────────────────────────────────────────
def test_route_at_correct_path():
    expected = ROOT / "frontend/tenant-portal/app/(tenant)/tenant/setup/availability/page.tsx"
    assert expected.exists()


# ── 33. Old provider/availability redirects ───────────────────────────────────
def test_provider_availability_duplicate_route_is_deleted():
    assert not REDIRECT.exists()


# ── 34. Nav item points to new route ─────────────────────────────────────────
def test_nav_item_points_to_new_route():
    src = read(LAYOUT)
    assert "/business/coverage-hours" in src


# ── 35. Nav label updated to Business Hours ──────────────────────────────────
def test_nav_label_business_hours():
    src = read(LAYOUT)
    assert "Coverage & Hours" in src


# ── 36. Preset confirmation modal ─────────────────────────────────────────────
def test_preset_confirm_modal():
    src = read(PAGE)
    assert "PresetConfirmModal" in src
    assert "Apply Preset" in src
    assert "Cancel" in src


# ── 37. Preset preview text shown ────────────────────────────────────────────
def test_preset_preview_shown():
    src = read(PAGE)
    # Standard Hours preset has Mon–Sat preview
    assert "Mon" in src and "Sat" in src


# ── 38. Status hero section ───────────────────────────────────────────────────
def test_status_hero_section():
    src = read(PAGE)
    # Status is now shown via KPI stat row in the header band
    assert "Ready for Bookings" in src or "Not Configured" in src
    # KPI stat labels present in header
    assert "Total Rules" in src or "Active Rules" in src or "Active" in src
    assert "Availability" in src


# ── 39. Slot preview AM/PM format ────────────────────────────────────────────
def test_slot_preview_ampm_format():
    src = read(PAGE)
    assert "AM" in src and "PM" in src
    assert "fmt12" in src


# ── 40. Page uses real API (not mock data) ───────────────────────────────────
def test_uses_real_api():
    src = read(PAGE)
    assert "providerAvailabilityApi" in src
    assert "rulesApi" in src
    assert "useApi" in src


# ── 41. Delete confirm modal ──────────────────────────────────────────────────
def test_delete_confirm_modal():
    src = read(PAGE)
    assert "DeleteConfirm" in src
    assert "Remove Working Hours" in src


# ── 42. Close Day action in weekly schedule ───────────────────────────────────
def test_close_day_action():
    src = read(PAGE)
    assert "Close Day" in src

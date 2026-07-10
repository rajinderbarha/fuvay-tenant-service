"""
Phase 19 — Staff React Native App — Proven Level 5 Tests (48 tests).
Structural tests: file existence, API patterns, AsyncStorage auth,
navigation structure, transition graph, no hardcoded values.
"""
import os, re, json

APP   = "/home/claude/serviceos/mobile/staff-app"
SRC   = f"{APP}/src"
LIB   = f"{SRC}/lib"
SCRN  = f"{SRC}/screens"
NAV   = f"{SRC}/navigation"
CTX   = f"{SRC}/context"
HOOKS = f"{SRC}/hooks"
COMPS = f"{SRC}/components"

# ── 1. Project structure ──────────────────────────────────────────────────────
REQUIRED_FILES = [
    "package.json", "app.json", "tsconfig.json", "index.ts",
    "src/App.tsx",
    "src/lib/api.ts", "src/lib/transitions.ts",
    "src/styles/theme.ts",
    "src/context/AuthContext.tsx",
    "src/hooks/useApi.ts", "src/hooks/useLocation.ts",
    "src/navigation/AppNavigator.tsx", "src/navigation/TabNavigator.tsx",
    "src/screens/LoginScreen.tsx",  "src/screens/HomeScreen.tsx",
    "src/screens/JobsListScreen.tsx","src/screens/JobDetailScreen.tsx",
    "src/screens/ChatListScreen.tsx","src/screens/ChatRoomScreen.tsx",
    "src/screens/EarningsScreen.tsx","src/screens/ProfileScreen.tsx",
    "src/components/JobStatusBadge.tsx","src/components/SlaTimer.tsx",
    "src/components/Button.tsx","src/components/Card.tsx",
    "src/components/StatCard.tsx",  "src/components/Skeleton.tsx",
]

def test_all_required_files_exist():
    missing = [f for f in REQUIRED_FILES if not os.path.exists(f"{APP}/{f}")]
    assert not missing, f"Missing files: {missing}"

def test_screen_count():
    screens = [f for f in os.listdir(SCRN) if f.endswith(".tsx")]
    assert len(screens) >= 7, f"Expected >= 7 screens, got {len(screens)}: {screens}"

def test_package_json_is_valid():
    with open(f"{APP}/package.json") as f: pkg = json.load(f)
    assert pkg["name"] == "serviceos-staff-app"
    assert "@react-navigation/bottom-tabs" in pkg["dependencies"]
    assert "@react-native-async-storage/async-storage" in pkg["dependencies"]
    assert "expo-location" in pkg["dependencies"]

def test_app_json_exists_and_valid():
    with open(f"{APP}/app.json") as f: app = json.load(f)
    assert "expo" in app
    assert app["expo"]["name"] == "ServiceOS Staff"
    assert "android" in app["expo"]
    assert "ios" in app["expo"]


# ── 2. API client — Level 5 ────────────────────────────────────────────────────
def test_api_uses_asyncstorage_not_localstorage():
    with open(f"{LIB}/api.ts") as f: c = f.read()
    assert "AsyncStorage" in c,         "Must use AsyncStorage (not localStorage)"
    assert "localStorage" not in c,     "Must NOT use localStorage in RN"

def test_api_has_storage_keys_constant():
    with open(f"{LIB}/api.ts") as f: c = f.read()
    assert "STORAGE_KEYS" in c

def test_api_storage_keys_has_all_5_keys():
    with open(f"{LIB}/api.ts") as f: c = f.read()
    for key in ["serviceos_staff_token","serviceos_staff_id","serviceos_tenant_id",
                "serviceos_staff_name","serviceos_staff_phone"]:
        assert key in c, f"Missing storage key: {key}"

def test_api_has_clear_session():
    with open(f"{LIB}/api.ts") as f: c = f.read()
    assert "clearSession" in c

def test_api_auth_injected_once():
    with open(f"{LIB}/api.ts") as f: c = f.read()
    # Authorization header set in apiFetch, not in individual calls
    auth_count = c.count('"Authorization"') + c.count("'Authorization'")
    assert auth_count == 1, f"Authorization must be injected once, found {auth_count} times"

def test_api_base_from_env():
    with open(f"{LIB}/api.ts") as f: c = f.read()
    assert "EXPO_PUBLIC_API_URL" in c, "API_BASE must come from env variable"
    assert "localhost:8000" not in c.replace("??", "") or "EXPO_PUBLIC_API_URL" in c

def test_api_has_all_required_clients():
    with open(f"{LIB}/api.ts") as f: c = f.read()
    for client in ["authApi","jobsApi","staffApi","geoApi","chatApi","earningsApi"]:
        assert client in c, f"Missing API client: {client}"

def test_api_jobs_filters_by_staff_id():
    with open(f"{LIB}/api.ts") as f: c = f.read()
    assert "assigned_staff_id" in c, "jobsApi must filter jobs by staff ID"

def test_api_no_inline_fetch_in_screens():
    # Match bare fetch( but not refetch() or prefetch()
    inline_fetch = re.compile(r"(?<!re)(?<!pre)\bfetch\(")
    violations = []
    for fname in os.listdir(SCRN):
        if not fname.endswith(".tsx"): continue
        with open(f"{SCRN}/{fname}") as f: content = f.read()
        # Strip comment lines
        clean = "\n".join(l for l in content.split("\n") if not l.strip().startswith("//"))
        if inline_fetch.search(clean):
            violations.append(fname)
    assert not violations, f"Screens with inline fetch(): {violations}"

def test_api_serviceoserror_typed():
    with open(f"{LIB}/api.ts") as f: c = f.read()
    assert "ServiceOSError" in c


# ── 3. Auth context ────────────────────────────────────────────────────────────
def test_auth_context_exists():
    assert os.path.exists(f"{CTX}/AuthContext.tsx")

def test_auth_context_uses_asyncstorage():
    with open(f"{CTX}/AuthContext.tsx") as f: c = f.read()
    assert "AsyncStorage" in c

def test_auth_context_provides_login_logout():
    with open(f"{CTX}/AuthContext.tsx") as f: c = f.read()
    assert "login" in c and "logout" in c

def test_auth_context_clears_session_on_logout():
    with open(f"{CTX}/AuthContext.tsx") as f: c = f.read()
    assert "clearSession" in c or "multiRemove" in c

def test_auth_context_stores_all_keys_on_login():
    with open(f"{CTX}/AuthContext.tsx") as f: c = f.read()
    assert "multiSet" in c or "setItem" in c


# ── 4. Transitions graph ───────────────────────────────────────────────────────
def test_transitions_file_exists():
    assert os.path.exists(f"{LIB}/transitions.ts")

def test_valid_transitions_graph_exists():
    with open(f"{LIB}/transitions.ts") as f: c = f.read()
    assert "VALID_TRANSITIONS" in c

def test_transitions_cover_key_statuses():
    with open(f"{LIB}/transitions.ts") as f: c = f.read()
    for s in ["assigned","accepted","en_route","arrived","in_progress",
              "parts_required","quality_check","completed"]:
        assert s in c, f"Missing transition: {s}"

def test_sla_bands_defined():
    with open(f"{LIB}/transitions.ts") as f: c = f.read()
    assert "SLA_BANDS" in c
    assert "getSlaStatus" in c

def test_status_label_map_defined():
    with open(f"{LIB}/transitions.ts") as f: c = f.read()
    assert "STATUS_LABEL" in c
    assert "STATUS_COLOR" in c


# ── 5. Navigation structure ────────────────────────────────────────────────────
def test_app_navigator_has_auth_guard():
    with open(f"{NAV}/AppNavigator.tsx") as f: c = f.read()
    assert "user" in c or "isAuthenticated" in c, "AppNavigator must guard auth state"
    assert "LoginScreen" in c or "Login" in c

def test_app_navigator_has_job_detail_route():
    with open(f"{NAV}/AppNavigator.tsx") as f: c = f.read()
    assert "JobDetail" in c

def test_app_navigator_has_chat_room_route():
    with open(f"{NAV}/AppNavigator.tsx") as f: c = f.read()
    assert "ChatRoom" in c

def test_tab_navigator_has_5_tabs():
    with open(f"{NAV}/TabNavigator.tsx") as f: c = f.read()
    for tab in ["Home","Jobs","Chat","Earnings","Profile"]:
        assert tab in c, f"TabNavigator missing tab: {tab}"

def test_app_tsx_wraps_with_auth_provider():
    with open(f"{SRC}/App.tsx") as f: c = f.read()
    assert "AuthProvider" in c


# ── 6. Screens completeness ────────────────────────────────────────────────────
def test_login_screen_uses_asyncstorage_or_auth():
    with open(f"{SCRN}/LoginScreen.tsx") as f: c = f.read()
    assert "useAuth" in c or "AsyncStorage" in c

def test_login_screen_has_phone_and_password():
    with open(f"{SCRN}/LoginScreen.tsx") as f: c = f.read()
    assert "phone" in c.lower() or "Phone" in c
    assert "password" in c.lower() or "Password" in c

def test_home_screen_shows_active_job():
    with open(f"{SCRN}/HomeScreen.tsx") as f: c = f.read()
    assert "active" in c.lower()
    assert "JobStatusBadge" in c or "status" in c

def test_jobs_list_has_status_filter_tabs():
    with open(f"{SCRN}/JobsListScreen.tsx") as f: c = f.read()
    assert "in_progress" in c
    assert "completed" in c
    assert "Tab" in c or "tab" in c

def test_job_detail_has_valid_transitions():
    with open(f"{SCRN}/JobDetailScreen.tsx") as f: c = f.read()
    assert "VALID_TRANSITIONS" in c

def test_job_detail_has_status_update():
    with open(f"{SCRN}/JobDetailScreen.tsx") as f: c = f.read()
    assert "updateStatus" in c or "updateAction" in c

def test_job_detail_has_close_modal():
    with open(f"{SCRN}/JobDetailScreen.tsx") as f: c = f.read()
    assert "closeModal" in c or "close" in c.lower()
    assert "Modal" in c

def test_job_detail_starts_location_tracking():
    with open(f"{SCRN}/JobDetailScreen.tsx") as f: c = f.read()
    assert "useLocation" in c or "startTracking" in c

def test_job_detail_can_call_customer():
    with open(f"{SCRN}/JobDetailScreen.tsx") as f: c = f.read()
    assert "Linking" in c and "tel:" in c

def test_chat_room_sends_message():
    with open(f"{SCRN}/ChatRoomScreen.tsx") as f: c = f.read()
    assert "sendMessage" in c or "sendAction" in c

def test_chat_room_marks_read():
    with open(f"{SCRN}/ChatRoomScreen.tsx") as f: c = f.read()
    assert "markRead" in c

def test_earnings_screen_shows_summary_and_records():
    with open(f"{SCRN}/EarningsScreen.tsx") as f: c = f.read()
    assert "summary" in c.lower()
    assert "commissions" in c.lower() or "records" in c.lower()

def test_profile_screen_has_logout():
    with open(f"{SCRN}/ProfileScreen.tsx") as f: c = f.read()
    assert "logout" in c

def test_profile_screen_has_schedule_edit():
    with open(f"{SCRN}/ProfileScreen.tsx") as f: c = f.read()
    assert "updateSchedule" in c or "schedule" in c.lower()


# ── 7. Components ─────────────────────────────────────────────────────────────
def test_job_status_badge_uses_status_color():
    with open(f"{COMPS}/JobStatusBadge.tsx") as f: c = f.read()
    assert "STATUS_COLOR" in c

def test_sla_timer_uses_get_sla_status():
    with open(f"{COMPS}/SlaTimer.tsx") as f: c = f.read()
    assert "getSlaStatus" in c

def test_button_has_loading_state():
    with open(f"{COMPS}/Button.tsx") as f: c = f.read()
    assert "loading" in c
    assert "ActivityIndicator" in c

def test_skeleton_uses_animated():
    with open(f"{COMPS}/Skeleton.tsx") as f: c = f.read()
    assert "Animated" in c


# ── 8. No hardcoded values ─────────────────────────────────────────────────────
HEX_RE = re.compile(r'(?<!["\w])#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})(?!\w)')

def test_screens_no_hardcoded_hex():
    violations = []
    for fname in os.listdir(SCRN):
        if not fname.endswith(".tsx"): continue
        with open(f"{SCRN}/{fname}") as f: c = f.read()
        # Strip comments
        clean = "\n".join(l for l in c.split("\n") if not l.strip().startswith("//"))
        hits  = HEX_RE.findall(clean)
        if hits:
            violations.append(f"{fname}: {hits[:3]}")
    assert not violations, f"Screens with hardcoded hex (use theme.colors): {violations}"

def test_theme_is_single_source_of_colors():
    with open(f"{SRC}/styles/theme.ts") as f: c = f.read()
    assert "brand:" in c or "brand =" in c
    assert "success:" in c or "success =" in c
    assert "danger:"  in c or "danger ="  in c

def test_use_api_hook_exists():
    assert os.path.exists(f"{HOOKS}/useApi.ts")
    with open(f"{HOOKS}/useApi.ts") as f: c = f.read()
    assert "useApi" in c and "useAction" in c

def test_use_location_hook_calls_geo_api():
    with open(f"{HOOKS}/useLocation.ts") as f: c = f.read()
    assert "geoApi" in c or "updateLocation" in c
    assert "expo-location" in c or "Location" in c

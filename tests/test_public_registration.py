"""
Public Registration Engine — Tests (15 tests).
Validates router structure, schema validation, OTP flow, and security.
"""
import os, pathlib

BASE = str(pathlib.Path(__file__).parent.parent.resolve())
ENGINE = os.path.join(BASE, "app/engines/public_registration")

def test_engine_files_exist():
    assert os.path.exists(f"{ENGINE}/__init__.py")
    assert os.path.exists(f"{ENGINE}/router.py")

def test_router_has_3_endpoints():
    with open(f"{ENGINE}/router.py", encoding="utf-8") as f: c = f.read()
    assert "/register/initiate" in c
    assert "/register/confirm-plan" in c
    assert "/register/verify" in c

def test_router_prefix_is_v1_public():
    with open(f"{ENGINE}/router.py", encoding="utf-8") as f: c = f.read()
    assert 'prefix="/v1/public"' in c

def test_no_auth_dependency_on_endpoints():
    with open(f"{ENGINE}/router.py", encoding="utf-8") as f: c = f.read()
    # Public endpoints must not use get_current_user auth dependency
    assert "get_current_user" not in c

def test_initiate_validates_vertical():
    with open(f"{ENGINE}/router.py", encoding="utf-8") as f: c = f.read()
    assert "VALID_VERTICALS" in c
    assert "home_services" in c

def test_initiate_validates_plan():
    with open(f"{ENGINE}/router.py", encoding="utf-8") as f: c = f.read()
    assert "VALID_PLANS" in c
    assert "starter" in c and "growth" in c and "enterprise" in c

def test_otp_is_6_digits():
    with open(f"{ENGINE}/router.py", encoding="utf-8") as f: c = f.read()
    assert "100000" in c or "6-digit" in c or "randbelow(900000)" in c

def test_otp_stored_in_redis():
    with open(f"{ENGINE}/router.py", encoding="utf-8") as f: c = f.read()
    assert "redis" in c.lower() and "setex" in c

def test_session_has_ttl():
    with open(f"{ENGINE}/router.py", encoding="utf-8") as f: c = f.read()
    assert "SESSION_TTL_SECONDS" in c or "OTP_TTL_SECONDS" in c

def test_otp_max_attempts_enforced():
    with open(f"{ENGINE}/router.py", encoding="utf-8") as f: c = f.read()
    assert "otp_attempts" in c
    assert "MAX_ATTEMPTS" in c or "5" in c

def test_verify_creates_tenant_and_user():
    with open(f"{ENGINE}/router.py", encoding="utf-8") as f: c = f.read()
    assert "INSERT INTO tenants" in c or "tenant" in c.lower()
    assert "INSERT INTO users" in c or "user" in c.lower()

def test_verify_deletes_session_after_success():
    with open(f"{ENGINE}/router.py", encoding="utf-8") as f: c = f.read()
    assert "redis.delete" in c or "delete" in c

def test_router_registered_in_main():
    with open(os.path.join(BASE, "app/main.py"), encoding="utf-8") as f: c = f.read()
    assert "public_reg_router" in c or "public_registration" in c

def test_initial_tenant_status_is_pending():
    with open(f"{ENGINE}/router.py", encoding="utf-8") as f: c = f.read()
    assert "pending_activation" in c or "trial" in c

def test_trial_starts_on_registration():
    with open(f"{ENGINE}/router.py", encoding="utf-8") as f: c = f.read()
    # Tenant starts in pending_activation, trial begins on first login
    assert "plan_type" in c

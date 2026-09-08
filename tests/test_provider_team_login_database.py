"""Opt-in local PostgreSQL integration; all fixtures and writes roll back."""
import os
import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import get_settings
from app.dependencies.auth import UserContext
from app.engines.auth.models import User, UserSession
from app.engines.auth.service import AuthService
from app.engines.auth.utils import verify_password
from app.engines.provider_portal.team_login_service import generate_team_password, set_login_enabled


@pytest.mark.asyncio
@pytest.mark.skipif(os.getenv("RUN_LOCAL_TEAM_LOGIN_DB_TEST") != "1", reason="Opt-in local PostgreSQL test")
async def test_team_credentials_persist_hash_change_regenerate_disable_restore():
    from sqlalchemy.engine import make_url
    url = make_url(get_settings().DATABASE_URL)
    assert url.host in {"localhost", "127.0.0.1", "::1"}, "Only run against local development DB"
    engine = create_async_engine(url, echo=False)
    try:
        async with engine.connect() as connection:
            outer = await connection.begin()
            try:
                async with AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint") as db:
                    owner = (await db.execute(select(User).where(User.role == "tenant_owner", User.is_active.is_(True), User.tenant_id.is_not(None)).limit(1))).scalar_one()
                    actor = UserContext(user_id=str(owner.id), email=owner.email, role="tenant_owner",
                                        tenant_id=str(owner.tenant_id), full_name=owner.full_name, is_verified=True)
                    mid = uuid.uuid4()
                    email = f"login-regression-{mid.hex}@example.test"
                    await db.execute(text("""
                        INSERT INTO provider_team_members (id,tenant_id,full_name,email,member_type,status,can_receive_assignment)
                        VALUES (:id,:tid,'Regression Fixture',:email,'staff','active',false)
                    """), {"id": mid, "tid": owner.tenant_id, "email": email})
                    result = await generate_team_password(db, mid, owner.tenant_id, actor, "regression-test", None)
                    account = await db.get(User, uuid.UUID(result["user_id"]))
                    assert account and account.role == "staff" and account.is_active
                    assert verify_password(result["temporary_password"], account.hashed_password)
                    assert account.force_password_change and account.temporary_password_active
                    linked = (await db.execute(text("SELECT user_id,username FROM provider_team_members WHERE id=:id"), {"id": mid})).one()
                    assert linked.user_id == account.id and linked.username == email
                    changed = await AuthService(db).change_password_required(account.id, result["temporary_password"], "New-Secure-Fixture89!")
                    assert changed["password_changed"] and not account.force_password_change
                    session = UserSession(user_id=account.id, tenant_id=owner.tenant_id,
                                          device_id="regression-fixture", device_name="Regression Fixture", is_approved=True)
                    db.add(session)
                    await db.flush()
                    regenerated = await generate_team_password(db, mid, owner.tenant_id, actor, "regression-test", None)
                    assert regenerated["user_id"] == result["user_id"]
                    assert verify_password(regenerated["temporary_password"], account.hashed_password)
                    assert not verify_password("New-Secure-Fixture89!", account.hashed_password)
                    assert session.revoked_at is not None
                    await set_login_enabled(db, mid, owner.tenant_id, actor.user_id, False)
                    await db.flush()
                    assert not account.is_active
                    await set_login_enabled(db, mid, owner.tenant_id, actor.user_id, True)
                    await db.flush()
                    assert account.is_active
            finally:
                await outer.rollback()
    finally:
        await engine.dispose()

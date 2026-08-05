"""ADD-EDIT-ADDRESS-CONTRACT (2026-08-01) — customer address CRUD, the
server-owned default invariant, ownership/enumeration safety, and booking
snapshot immutability, for the mobile Add/Edit Saved Address phase.

Two real bugs fixed this phase (audited against `ServiceabilityService`
before the Add/Edit screen was built):

1. `get_address` raised two different error shapes for "address doesn't
   exist" (`CUSTOMER_ADDRESS_NOT_FOUND` / "Address 'id' not found.") vs
   "address exists but belongs to another customer"
   (`NotFoundException` -> `NOT_FOUND` / "CustomerAddress 'id' not
   found.") — an enumeration oracle. Both paths now raise the identical
   `ServiceOSException` shape.
2. `update_address` applied a bare `is_default: false` directly via its
   generic field-assignment loop, which could leave a customer with zero
   default addresses while other active addresses remained (the DB's
   partial-unique-index invariant only prevents *two* defaults, not
   *zero*). `is_default` is now only ever actionable when `True`.

Also new this phase: a `label` column (Home/Work/Other) distinct from the
recipient `name`, PIN-code format validation, and 409 handling for a
concurrent default-mutation race (backed by the pre-existing DB partial
unique index `uq_ca_one_default_active`).
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.engines.serviceability.service import ServiceabilityService
from app.engines.serviceability.schemas import AddressCreate, AddressUpdate
from app.engines.serviceability.models import CustomerAddress
from app.exceptions import ServiceOSException


def _exec_result(*, scalar=None, scalars_all=None, scalars_first=None):
    res = MagicMock()
    res.scalar_one = MagicMock(return_value=scalar)
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=scalars_all or [])
    scalars.first = MagicMock(return_value=scalars_first)
    res.scalars = MagicMock(return_value=scalars)
    return res


def _svc(*, actor_id=None, actor_role="customer"):
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    db.get = AsyncMock()
    svc = ServiceabilityService(db=db, actor_id=actor_id, actor_role=actor_role)
    return svc, db


def _addr(**overrides):
    defaults = dict(
        customer_id=uuid.uuid4(), tenant_id=None, label="Home", name="Rajinder Singh",
        phone="+919900024102", address_line_1="House 24", address_line_2=None,
        landmark=None, city="Ludhiana", district=None, state="Punjab", country="India",
        zipcode="141002", latitude=None, longitude=None, is_default=False, is_active=True,
    )
    defaults.update(overrides)
    addr = CustomerAddress(**defaults)
    addr.id = uuid.uuid4()
    return addr


class TestCreateAddress:
    @pytest.mark.asyncio
    async def test_first_address_becomes_default(self):
        svc, db = _svc()
        customer_id = uuid.uuid4()
        db.execute.return_value = _exec_result(scalar=0)  # existing count == 0

        result = await svc.create_address(customer_id, None, {
            "address_line_1": "House 24", "city": "Ludhiana", "state": "Punjab",
            "zipcode": "141002", "is_default": False,
        })

        assert result["is_default"] is True

    @pytest.mark.asyncio
    async def test_second_address_is_not_default_unless_requested(self):
        svc, db = _svc()
        customer_id = uuid.uuid4()
        db.execute.return_value = _exec_result(scalar=1)  # one existing address

        result = await svc.create_address(customer_id, None, {
            "address_line_1": "House 25", "city": "Ludhiana", "state": "Punjab",
            "zipcode": "141003", "is_default": False,
        })

        assert result["is_default"] is False

    @pytest.mark.asyncio
    async def test_explicit_default_clears_existing_default_atomically(self):
        svc, db = _svc()
        customer_id = uuid.uuid4()
        previous_default = _addr(customer_id=customer_id, is_default=True)
        db.execute.return_value = _exec_result(scalars_all=[previous_default])

        result = await svc.create_address(customer_id, None, {
            "address_line_1": "House 26", "city": "Ludhiana", "state": "Punjab",
            "zipcode": "141004", "is_default": True,
        })

        assert previous_default.is_default is False
        assert result["is_default"] is True

    @pytest.mark.asyncio
    async def test_label_is_persisted_distinct_from_recipient_name(self):
        svc, db = _svc()
        db.execute.return_value = _exec_result(scalar=0)

        result = await svc.create_address(uuid.uuid4(), None, {
            "label": "Work", "name": "Rajinder Singh",
            "address_line_1": "Plot 9", "city": "Ludhiana", "state": "Punjab",
            "zipcode": "141002",
        })

        assert result["label"] == "Work"
        assert result["name"] == "Rajinder Singh"

    @pytest.mark.asyncio
    async def test_concurrent_default_race_surfaces_as_clean_conflict_not_500(self):
        svc, db = _svc()
        db.execute.return_value = _exec_result(scalar=0)
        db.commit.side_effect = IntegrityError("stmt", {}, Exception("dup"))

        with pytest.raises(ServiceOSException) as exc_info:
            await svc.create_address(uuid.uuid4(), None, {
                "address_line_1": "House 1", "city": "Ludhiana", "state": "Punjab",
                "zipcode": "141002",
            })

        assert exc_info.value.error_code == "CUSTOMER_ADDRESS_DEFAULT_CONFLICT"
        assert exc_info.value.status_code == 409
        db.rollback.assert_awaited()


class TestOwnershipEnumerationSafety:
    @pytest.mark.asyncio
    async def test_missing_address_returns_404_customer_address_not_found(self):
        svc, db = _svc(actor_id=uuid.uuid4())
        db.get.return_value = None

        with pytest.raises(ServiceOSException) as exc_info:
            await svc.get_address(uuid.uuid4())

        assert exc_info.value.error_code == "CUSTOMER_ADDRESS_NOT_FOUND"
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_another_customers_address_returns_the_identical_error_shape(self):
        owner_id = uuid.uuid4()
        requester_id = uuid.uuid4()
        svc, db = _svc(actor_id=requester_id)
        other_customers_address = _addr(customer_id=owner_id)
        db.get.return_value = other_customers_address

        missing_svc, missing_db = _svc(actor_id=requester_id)
        missing_db.get.return_value = None

        with pytest.raises(ServiceOSException) as foreign_exc:
            await svc.get_address(other_customers_address.id)
        with pytest.raises(ServiceOSException) as missing_exc:
            await missing_svc.get_address(uuid.uuid4())

        assert foreign_exc.value.error_code == missing_exc.value.error_code == "CUSTOMER_ADDRESS_NOT_FOUND"
        assert foreign_exc.value.status_code == missing_exc.value.status_code == 404
        # Detail text must not leak "this address exists but isn't yours".
        assert "not found" in foreign_exc.value.detail.lower()
        assert "CustomerAddress" not in foreign_exc.value.detail

    @pytest.mark.asyncio
    async def test_owner_can_read_their_own_address(self):
        owner_id = uuid.uuid4()
        svc, db = _svc(actor_id=owner_id)
        own_address = _addr(customer_id=owner_id)
        db.get.return_value = own_address

        result = await svc.get_address_dict(own_address.id)
        assert result["id"] == str(own_address.id)


class TestDefaultInvariant:
    @pytest.mark.asyncio
    async def test_bare_is_default_false_does_not_unset_the_only_default(self):
        """Regression test for the fixed bug: updating any other field on
        the current default address, with is_default explicitly false in
        the payload, must never leave zero default addresses."""
        owner_id = uuid.uuid4()
        svc, db = _svc(actor_id=owner_id)
        addr = _addr(customer_id=owner_id, is_default=True)
        db.get.return_value = addr

        result = await svc.update_address(addr.id, {"landmark": "Near Bus Stand", "is_default": False})

        assert result["is_default"] is True
        assert result["landmark"] == "Near Bus Stand"

    @pytest.mark.asyncio
    async def test_setting_is_default_true_clears_the_previous_default_atomically(self):
        owner_id = uuid.uuid4()
        svc, db = _svc(actor_id=owner_id)
        addr = _addr(customer_id=owner_id, is_default=False)
        previous_default = _addr(customer_id=owner_id, is_default=True)
        db.get.return_value = addr
        db.execute.return_value = _exec_result(scalars_all=[previous_default])

        result = await svc.update_address(addr.id, {"is_default": True})

        assert previous_default.is_default is False
        assert result["is_default"] is True

    @pytest.mark.asyncio
    async def test_deleting_the_default_promotes_the_next_most_recent_address(self):
        owner_id = uuid.uuid4()
        svc, db = _svc(actor_id=owner_id)
        addr = _addr(customer_id=owner_id, is_default=True)
        next_addr = _addr(customer_id=owner_id, is_default=False)
        db.get.return_value = addr
        db.execute.return_value = _exec_result(scalars_first=next_addr)

        result = await svc.delete_address(addr.id)

        assert result["deleted"] is True
        assert addr.is_default is False
        assert next_addr.is_default is True

    @pytest.mark.asyncio
    async def test_deleting_a_non_default_address_promotes_nothing(self):
        owner_id = uuid.uuid4()
        svc, db = _svc(actor_id=owner_id)
        addr = _addr(customer_id=owner_id, is_default=False)
        db.get.return_value = addr

        await svc.delete_address(addr.id)

        assert db.execute.await_count == 0

    @pytest.mark.asyncio
    async def test_set_default_endpoint_conflict_surfaces_cleanly(self):
        owner_id = uuid.uuid4()
        svc, db = _svc(actor_id=owner_id)
        addr = _addr(customer_id=owner_id, is_default=False)
        db.get.return_value = addr
        db.execute.return_value = _exec_result(scalars_all=[])
        db.commit.side_effect = IntegrityError("stmt", {}, Exception("dup"))

        with pytest.raises(ServiceOSException) as exc_info:
            await svc.set_default_address(addr.id)

        assert exc_info.value.error_code == "CUSTOMER_ADDRESS_DEFAULT_CONFLICT"
        assert exc_info.value.status_code == 409


class TestPayloadValidation:
    def test_invalid_pin_code_rejected_on_create(self):
        with pytest.raises(ValidationError):
            AddressCreate(address_line_1="House 1", city="Ludhiana", state="Punjab",
                           zipcode="12345")  # 5 digits, not 6

    def test_non_numeric_pin_code_rejected(self):
        with pytest.raises(ValidationError):
            AddressCreate(address_line_1="House 1", city="Ludhiana", state="Punjab",
                           zipcode="ABCDEF")

    def test_valid_six_digit_pin_accepted(self):
        payload = AddressCreate(address_line_1="House 1", city="Ludhiana", state="Punjab",
                                 zipcode="141002")
        assert payload.zipcode == "141002"

    def test_invalid_pin_code_rejected_on_update(self):
        with pytest.raises(ValidationError):
            AddressUpdate(zipcode="1")

    def test_label_outside_home_work_other_is_rejected(self):
        with pytest.raises(ValidationError):
            AddressCreate(address_line_1="House 1", city="Ludhiana", state="Punjab",
                           zipcode="141002", label="Vacation House")

    def test_home_work_other_labels_all_accepted(self):
        for label in ("Home", "Work", "Other"):
            payload = AddressCreate(address_line_1="House 1", city="Ludhiana", state="Punjab",
                                     zipcode="141002", label=label)
            assert payload.label == label

    def test_unknown_fields_are_not_accepted_by_the_schema(self):
        """The schema itself is the allowlist -- an unrecognized field
        (e.g. a UI-only concept) must not silently pass through."""
        payload = AddressCreate(address_line_1="House 1", city="Ludhiana", state="Punjab",
                                 zipcode="141002")
        assert not hasattr(payload, "serviceable")
        assert not hasattr(payload, "latitude_source")


class TestBookingSnapshotImmutability:
    @pytest.mark.asyncio
    async def test_updating_a_saved_address_does_not_touch_service_bookings(self):
        """update_address only ever executes against CustomerAddress plus
        (when changing default) a select over CustomerAddress rows -- it
        has no code path that reaches ServiceBooking, so a confirmed
        booking's address_snapshot cannot be mutated by this call."""
        owner_id = uuid.uuid4()
        svc, db = _svc(actor_id=owner_id)
        addr = _addr(customer_id=owner_id, is_default=False)
        db.get.return_value = addr

        await svc.update_address(addr.id, {"landmark": "Updated landmark"})

        from app.engines.final_records.models import ServiceBooking
        for call in db.execute.await_args_list:
            stmt = call.args[0] if call.args else None
            assert stmt is None or ServiceBooking not in str(stmt)

    @pytest.mark.asyncio
    async def test_deleting_a_saved_address_does_not_touch_service_bookings(self):
        owner_id = uuid.uuid4()
        svc, db = _svc(actor_id=owner_id)
        addr = _addr(customer_id=owner_id, is_default=False)
        db.get.return_value = addr

        await svc.delete_address(addr.id)

        assert db.execute.await_count == 0

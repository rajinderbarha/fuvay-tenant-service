"""Give the demo customer (customer@serviceos.in) enough real data for the
Home screen's personalised sections to actually render.

WHY THIS EXISTS
---------------
Several Home sections are driven by per-customer state -- saved address,
booking history ("Book again"), service credit, unread notifications. The
demo customer has none of it, so those sections correctly render as empty
and cannot be reviewed or screenshotted while being built.

WHAT IT DOES / DOESN'T DO
-------------------------
* Idempotent: re-running updates the same rows (matched on a stable
  natural key) rather than piling up duplicates.
* Writes ONLY rows owned by this one demo customer. Never touches tenant,
  catalog, pricing or entitlement data, and never modifies another
  customer's records.
* Reuses the EXISTING tenant/category/service ids that are already live and
  bookable at 140412, so the seeded booking points at real, resolvable
  catalog rows instead of inventing orphans (the exact defect that left 8
  category-less "Air Conditioner" rows in master_services).
* Deliberately does NOT drive the real booking lifecycle (draft -> match ->
  confirm -> complete). That flow has side effects -- provider matching,
  credit deduction, notifications to the tenant -- that would be wrong to
  trigger for display fixtures. These rows are inserted directly and marked
  as seeded in their own reason/note fields so they are identifiable.

Run:  python scripts/seed_customer_home_demo.py
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import Settings

CUSTOMER_EMAIL = "customer@serviceos.in"

# Live, verified-bookable rows at 140412 (Guramrit). Reused rather than
# invented so every seeded record resolves to a real catalog entry.
TENANT_ID = "244beeec-fedc-452e-8054-317e45557d4d"
CATEGORY_AC = "59d8f3aa-932d-429e-93bd-8d4f2ed615c3"
SERVICE_AC = "3c6720b0-9bf6-4dbd-84cc-83d8058e18a2"      # AC Service
CATEGORY_PLUMBING = "405cd796-9c97-4465-8a17-e7137e34d268"
SERVICE_PIPE_REPAIR = "8c546b06-15ab-4496-94b9-fa5cb96538f8"

SEED_MARK = "seeded:customer-home-demo"


async def main() -> None:
    settings = Settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        cid = (await conn.execute(
            text("SELECT id FROM users WHERE email = :e"), {"e": CUSTOMER_EMAIL}
        )).scalar_one_or_none()
        if not cid:
            print(f"ABORT: {CUSTOMER_EMAIL} not found; run seed_demo_users.py first")
            return
        print(f"customer: {cid}")

        # ── Saved addresses ───────────────────────────────────────────────
        # Home is the default and its ZIP (140412) is the one with live
        # coverage, so the Home screen resolves to a serviceable location.
        for label, line1, zipcode, city, is_default in [
            ("home", "House 24, Green Enclave", "140412", "Bassi Pathana", True),
            ("work", "2nd Floor, Sector 17 Plaza", "160017", "Chandigarh", False),
        ]:
            existing = (await conn.execute(text("""
                SELECT id FROM customer_addresses
                WHERE customer_id = :cid AND label = :label
            """), {"cid": cid, "label": label})).scalar_one_or_none()
            params = {
                "cid": cid, "label": label, "line1": line1, "zip": zipcode,
                "city": city, "state": "Punjab" if zipcode == "140412" else "Chandigarh",
                "is_default": is_default, "name": "Rajinder Singh", "phone": "+919876500011",
            }
            if existing:
                await conn.execute(text("""
                    UPDATE customer_addresses
                    SET address_line_1=:line1, city=:city, state=:state, zipcode=:zip,
                        is_default=:is_default, is_active=TRUE, name=:name, phone=:phone,
                        updated_at=now()
                    WHERE id=:id
                """), {**params, "id": existing})
                print(f"  address  {label:5s} updated")
            else:
                await conn.execute(text("""
                    INSERT INTO customer_addresses
                        (customer_id, label, name, phone, address_line_1, city, state,
                         country, zipcode, is_default, is_active)
                    VALUES (:cid, :label, :name, :phone, :line1, :city, :state,
                            'India', :zip, :is_default, TRUE)
                """), params)
                print(f"  address  {label:5s} created")

        # ── Booking history (drives "Book again") ─────────────────────────
        # Two completed + one in-flight, so both the history row and the
        # active-booking card have something real to show.
        bookings = [
            ("BK-DEMO-0001", "completed", CATEGORY_AC, SERVICE_AC,
             "AC not cooling properly", 18),
            ("BK-DEMO-0002", "completed", CATEGORY_PLUMBING, SERVICE_PIPE_REPAIR,
             "Kitchen sink pipe leaking", 40),
            ("BK-DEMO-0003", "on_the_way", CATEGORY_AC, SERVICE_AC,
             "Annual AC servicing", 0),
        ]
        for number, status, cat, svc, summary, days_ago in bookings:
            existing = (await conn.execute(
                text("SELECT id FROM service_bookings WHERE booking_number = :n"),
                {"n": number},
            )).scalar_one_or_none()
            params = {
                "n": number, "cid": cid, "tid": TENANT_ID, "cat": cat, "svc": svc,
                "summary": summary, "status": status, "days": days_ago,
            }
            if existing:
                await conn.execute(text("""
                    UPDATE service_bookings
                    SET status=:status, issue_summary=:summary, updated_at=now()
                    WHERE id=:id
                """), {**params, "id": existing})
                print(f"  booking  {number} updated ({status})")
            else:
                await conn.execute(text("""
                    INSERT INTO service_bookings
                        (booking_number, draft_id, customer_id, tenant_id, category_id,
                         offering_id, customer_name, customer_phone, city, zipcode,
                         issue_summary, status, assignment_status, created_at, updated_at)
                    VALUES (:n, gen_random_uuid(), :cid, :tid, :cat, :svc,
                            'Rajinder Singh', '+919876500011', 'Bassi Pathana', '140412',
                            :summary, :status, 'unassigned',
                            now() - make_interval(days => :days),
                            now() - make_interval(days => :days))
                """), params)
                print(f"  booking  {number} created ({status}, {days_ago}d ago)")

        # ── Technician on the in-flight booking ───────────────────────────
        # The Home "My Booking" card shows the assigned technician and their
        # earned rating. Both read through the REAL chain the app uses --
        # service_jobs.assigned_staff_id -> provider_team_members, plus
        # staff_rating_summaries -- so this seeds the same rows a genuine
        # assignment would produce, not a shortcut field on the booking.
        booking_id = (await conn.execute(
            text("SELECT id FROM service_bookings WHERE booking_number = 'BK-DEMO-0003'"),
        )).scalar_one_or_none()
        if booking_id:
            staff_id = (await conn.execute(text("""
                SELECT id FROM provider_team_members
                WHERE tenant_id = :tid AND full_name = 'Rakesh Kumar'
            """), {"tid": TENANT_ID})).scalar_one_or_none()
            if not staff_id:
                staff_id = (await conn.execute(text("""
                    INSERT INTO provider_team_members
                        (tenant_id, member_type, full_name, designation, created_at, updated_at)
                    VALUES (:tid, 'technician', 'Rakesh Kumar', 'Service technician', now(), now())
                    RETURNING id
                """), {"tid": TENANT_ID})).scalar_one()
                print("  staff    Rakesh Kumar created")

            job_id = (await conn.execute(
                text("SELECT id FROM service_jobs WHERE booking_id = :b"), {"b": booking_id},
            )).scalar_one_or_none()
            if job_id:
                await conn.execute(text("""
                    UPDATE service_jobs
                    SET assigned_staff_id = :s, status = 'on_the_way', updated_at = now()
                    WHERE id = :id
                """), {"s": staff_id, "id": job_id})
                print("  job      updated (on_the_way, Rakesh Kumar)")
            else:
                await conn.execute(text("""
                    INSERT INTO service_jobs
                        (job_number, booking_id, tenant_id, category_id, offering_id,
                         assigned_staff_id, status, created_at, updated_at)
                    VALUES ('JOB-DEMO-0003', :b, :tid, :cat, :svc,
                            :s, 'on_the_way', now(), now())
                """), {"b": booking_id, "tid": TENANT_ID, "cat": CATEGORY_AC,
                       "svc": SERVICE_AC, "s": staff_id})
                print("  job      created (on_the_way, Rakesh Kumar)")

            # A rating only exists once reviews do -- seeded with a real
            # review count so the star is earned, not decorative.
            existing_rating = (await conn.execute(text("""
                SELECT id FROM staff_rating_summaries
                WHERE tenant_id = :tid AND staff_member_id = :s
            """), {"tid": TENANT_ID, "s": staff_id})).scalar_one_or_none()
            if existing_rating:
                await conn.execute(text("""
                    UPDATE staff_rating_summaries
                    SET total_reviews = 34, average_rating = 4.80, updated_at = now()
                    WHERE id = :id
                """), {"id": existing_rating})
                print("  rating   updated (4.80, 34 reviews)")
            else:
                await conn.execute(text("""
                    INSERT INTO staff_rating_summaries
                        (id, tenant_id, staff_member_id, total_reviews, average_rating, updated_at)
                    VALUES (gen_random_uuid(), :tid, :s, 34, 4.80, now())
                """), {"tid": TENANT_ID, "s": staff_id})
                print("  rating   created (4.80, 34 reviews)")

            # A real scheduled slot so the card's time row has something
            # genuine to show.
            await conn.execute(text("""
                UPDATE service_bookings
                SET preferred_date = CURRENT_DATE,
                    preferred_time_window = '10:30 AM',
                    updated_at = now()
                WHERE id = :id
            """), {"id": booking_id})
            print("  booking  BK-DEMO-0003 scheduled today 10:30 AM")

        # ── Service credit ────────────────────────────────────────────────
        existing = (await conn.execute(
            text("SELECT id FROM customer_service_credits WHERE credit_number = :n"),
            {"n": "CR-DEMO-0001"},
        )).scalar_one_or_none()
        if existing:
            await conn.execute(text("""
                UPDATE customer_service_credits
                SET remaining_amount=250.00, status='active', updated_at=now()
                WHERE id=:id
            """), {"id": existing})
            print("  credit   CR-DEMO-0001 updated (250 remaining)")
        else:
            await conn.execute(text("""
                INSERT INTO customer_service_credits
                    (credit_number, customer_id, tenant_id, amount, remaining_amount,
                     currency, credit_type, source, status, issued_reason,
                     customer_message, internal_note, valid_from, expires_at)
                VALUES ('CR-DEMO-0001', :cid, :tid, 250.00, 250.00, 'INR',
                        'goodwill', 'admin_manual', 'active',
                        'Goodwill credit for a delayed visit',
                        'We have added Rs.250 credit to your account.',
                        :mark, now(), now() + interval '180 days')
            """), {"cid": cid, "tid": TENANT_ID, "mark": SEED_MARK})
            print("  credit   CR-DEMO-0001 created (250)")

        # ── Unread notifications (drives the bell badge) ──────────────────
        notifs = [
            ("booking_update", "Technician on the way",
             "Your technician will arrive for Annual AC servicing shortly.", "info"),
            ("payment_reminder", "Invoice ready",
             "Your invoice for Kitchen sink pipe leaking is ready to pay.", "warning"),
        ]
        for ntype, title, body, severity in notifs:
            existing = (await conn.execute(text("""
                SELECT id FROM in_app_notifications
                WHERE user_id = :cid AND title = :title
            """), {"cid": cid, "title": title})).scalar_one_or_none()
            if existing:
                await conn.execute(text("""
                    UPDATE in_app_notifications
                    SET read_status='unread', read_at=NULL, updated_at=now()
                    WHERE id=:id
                """), {"id": existing})
                print(f"  notif    {title!r} reset to unread")
            else:
                await conn.execute(text("""
                    INSERT INTO in_app_notifications
                        (user_id, tenant_id, notification_type, title, body,
                         severity, read_status, vertical_key)
                    VALUES (:cid, :tid, :ntype, :title, :body, :sev, 'unread',
                            'home_services')
                """), {"cid": cid, "tid": TENANT_ID, "ntype": ntype,
                       "title": title, "body": body, "sev": severity})
                print(f"  notif    {title!r} created")

    await engine.dispose()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())

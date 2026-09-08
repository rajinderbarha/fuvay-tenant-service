"""Admin projection of the provider-owned roster, including members without login."""
from sqlalchemy import text
from app.engines.vertical_catalog.seat_enforcement import get_seat_usage


async def provider_team_projection(db, provider_id, page=1, page_size=20):
    rows = (await db.execute(text("""
        SELECT m.id,m.user_id,m.full_name,m.member_type,m.status,m.can_receive_assignment,
               m.availability_state,u.is_active AS login_enabled,
               (SELECT count(*) FROM service_jobs j WHERE j.tenant_id=m.tenant_id
                AND j.assigned_staff_id=m.user_id AND j.status NOT IN ('completed','cancelled','failed')) AS active_jobs
        FROM provider_team_members m LEFT JOIN users u ON u.id=m.user_id AND u.tenant_id=m.tenant_id
        WHERE m.tenant_id=:tid AND m.deleted_at IS NULL
        ORDER BY m.full_name,m.id
    """), {"tid": str(provider_id)})).mappings().all()
    seats = await get_seat_usage(db, provider_id)
    def available(row):
        return row["status"] == "active" and row["can_receive_assignment"] and row["availability_state"] == "available" and row["active_jobs"] == 0
    return {
        "total_staff": len(rows), "available_staff": sum(available(r) for r in rows),
        "suspended_staff": sum(r["status"] != "active" for r in rows),
        "technician_count": sum(r["member_type"] == "technician" for r in rows),
        "seat_usage": seats,
        "staff": [{"staff_id": str(r["id"]), "name": r["full_name"], "designation": r["member_type"],
                   "assignment_status": r["status"], "can_receive_assignment": r["can_receive_assignment"],
                   "availability_status": "available" if available(r) else "on_job" if r["active_jobs"] else "unavailable",
                   "login_status": "Not created" if not r["user_id"] else "Enabled" if r["login_enabled"] else "Disabled",
                   "is_active": r["status"] == "active"} for r in rows[(page-1)*page_size:page*page_size]],
        "page": page, "page_size": page_size,
    }

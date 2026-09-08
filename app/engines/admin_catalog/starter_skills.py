"""Explicit admin-managed starter catalog; never mutate skill data on provider reads."""
from sqlalchemy import text

HOME_SERVICE_SKILLS = (
    ("ac_diagnostics", "AC Diagnostics", "Diagnose cooling, electrical and airflow faults.", 10, True),
    ("ac_repair", "AC Repair", "Repair approved AC components after diagnosis.", 20, True),
    ("ac_installation", "AC Installation", "Install and commission supported AC systems.", 30, True),
    ("ac_uninstallation", "AC Uninstallation", "Safely disconnect and remove AC systems.", 40, True),
    ("ac_maintenance", "AC Maintenance / Servicing", "Perform preventive maintenance and routine servicing.", 50, False),
    ("ac_gas_refill", "AC Gas Refill", "Inspect, recover and recharge refrigerant.", 60, True),
    ("refrigerant_handling", "Refrigerant Handling", "Handle refrigerants using approved safety practices.", 70, True),
    ("electrical_safety", "Electrical Safety", "Apply electrical isolation and safe-work procedures.", 80, True),
)


async def add_starter_skills(db, category_id, actor_id):
    added = 0
    for code, name, description, order, verify in HOME_SERVICE_SKILLS:
        result = await db.execute(text("""
            INSERT INTO category_skills
                (category_id, code, name, description, status, requires_verification,
                 display_order, created_by_user_id, updated_by_user_id)
            SELECT :cid,:code,:name,:description,'active',:verify,:ordering,:actor,:actor
             WHERE NOT EXISTS (SELECT 1 FROM category_skills
                 WHERE category_id=:cid AND lower(name)=lower(:name))
            ON CONFLICT (category_id, code) DO NOTHING
        """), {"cid": str(category_id), "code": code, "name": name, "description": description,
               "verify": verify, "ordering": order, "actor": str(actor_id)})
        added += result.rowcount
    return added

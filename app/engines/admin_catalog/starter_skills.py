"""Explicit admin-managed starter catalog; never mutate skill data on provider reads.

Skills are qualifications, not service assignments. Each starter is tied to
the matching service group so a provider only sees qualifications relevant to
the services it has actually published.
"""
from sqlalchemy import text


# (group aliases, code, name, description, order, requires verification)
# Aliases are matched against the service-group code, slug and name. Admins
# can still add project-specific skills from the category workspace.
HOME_SERVICE_SKILLS = (
    (("ac", "air conditioner", "air conditioning", "hvac"), "ac_diagnostics", "AC Diagnostics", "Diagnose cooling, electrical and airflow faults.", 10, True),
    (("ac", "air conditioner", "air conditioning", "hvac"), "ac_repair", "AC Repair", "Repair approved AC components after diagnosis.", 20, True),
    (("ac", "air conditioner", "air conditioning", "hvac"), "ac_installation", "AC Installation", "Install and commission supported AC systems.", 30, True),
    (("ac", "air conditioner", "air conditioning", "hvac"), "ac_uninstallation", "AC Uninstallation", "Safely disconnect and remove AC systems.", 40, True),
    (("ac", "air conditioner", "air conditioning", "hvac"), "ac_maintenance", "AC Maintenance / Servicing", "Perform preventive maintenance and routine servicing.", 50, False),
    (("ac", "air conditioner", "air conditioning", "hvac"), "ac_gas_refill", "AC Gas Refill", "Inspect, recover and recharge refrigerant.", 60, True),
    (("ac", "air conditioner", "air conditioning", "hvac"), "refrigerant_handling", "Refrigerant Handling", "Handle refrigerants using approved safety practices.", 70, True),
    (("ac", "air conditioner", "air conditioning", "hvac"), "electrical_safety", "Electrical Safety", "Apply electrical isolation and safe-work procedures for AC systems.", 80, True),
    (("plumb",), "plumbing_diagnostics", "Plumbing Diagnostics", "Diagnose leaks, pressure, drainage and fixture faults.", 10, False),
    (("plumb",), "tap_fixture_repair", "Tap / Fixture Repair", "Repair and replace taps, faucets and small plumbing fixtures.", 20, False),
    (("plumb",), "basin_sink_installation", "Basin / Sink Installation", "Install wash basins, sinks, traps and associated fittings.", 30, True),
    (("plumb",), "toilet_commode_installation", "Toilet / Commode Installation", "Install and replace Indian and Western toilet fixtures.", 40, True),
    (("plumb",), "pipeline_installation_repair", "Pipeline Installation & Repair", "Install, reroute and repair domestic water pipelines.", 50, True),
    (("plumb",), "drainage_leak_repair", "Drainage & Leak Repair", "Locate and repair drainage blockages and water leaks.", 60, False),
    (("appliance",), "appliance_diagnostics", "Appliance Diagnostics", "Diagnose electrical and functional appliance faults.", 10, False),
    (("appliance",), "microwave_oven_repair", "Microwave Oven Repair", "Diagnose and repair supported microwave ovens.", 20, True),
    (("appliance",), "television_repair", "Television Repair", "Diagnose and repair supported television systems.", 30, True),
    (("appliance",), "appliance_electrical_safety", "Appliance Electrical Safety", "Use safe isolation and testing procedures for appliances.", 40, True),
    (("washing machine", "laundry"), "washing_machine_diagnostics", "Washing Machine Diagnostics", "Diagnose washing, draining, spinning and electrical faults.", 10, False),
    (("washing machine", "laundry"), "washing_machine_repair", "Washing Machine Repair", "Repair supported washing-machine components.", 20, True),
    (("washing machine", "laundry"), "washing_machine_installation", "Washing Machine Installation", "Install and commission washing machines safely.", 30, False),
    (("chimney", "hob"), "chimney_hob_diagnostics", "Chimney & Hob Diagnostics", "Diagnose suction, ignition, electrical and airflow faults.", 10, False),
    (("chimney", "hob"), "chimney_servicing_repair", "Chimney Servicing & Repair", "Service and repair kitchen chimney systems.", 20, True),
    (("chimney", "hob"), "chimney_installation", "Kitchen Chimney Installation", "Install and commission kitchen chimneys.", 30, True),
    (("chimney", "hob"), "hob_repair_installation", "Hob Repair & Installation", "Repair and install supported kitchen hobs.", 40, True),
    (("geyser", "water heater"), "water_heater_diagnostics", "Water Heater Diagnostics", "Diagnose heating, water-flow and electrical faults.", 10, False),
    (("geyser", "water heater"), "geyser_repair", "Geyser / Water Heater Repair", "Repair supported geyser and water-heater components.", 20, True),
    (("geyser", "water heater"), "geyser_installation", "Geyser / Water Heater Installation", "Install and commission water heaters safely.", 30, True),
    (("geyser", "water heater"), "water_heater_safety", "Water Heater Safety", "Apply electrical, pressure and water safety procedures.", 40, True),
    (("home security", "cctv", "security"), "cctv_diagnostics", "CCTV Diagnostics", "Diagnose camera, recorder, power and connectivity faults.", 10, False),
    (("home security", "cctv", "security"), "cctv_installation", "CCTV Installation", "Install and commission CCTV cameras and recorders.", 20, True),
    (("home security", "cctv", "security"), "cctv_repair", "CCTV Repair", "Repair supported CCTV equipment and connections.", 30, True),
    (("home security", "cctv", "security"), "cctv_network_cabling", "CCTV Network & Cabling", "Install and test CCTV power and data cabling.", 40, True),
    (("carpentry", "woodwork", "furniture"), "furniture_repair", "Furniture Repair", "Repair common furniture and joinery defects.", 10, False),
    (("carpentry", "woodwork", "furniture"), "furniture_assembly", "Furniture Assembly", "Assemble and safely install supported furniture.", 20, False),
    (("carpentry", "woodwork", "furniture"), "carpentry_installation", "Carpentry Installation", "Measure, fit and install common woodwork items.", 30, True),
    (("carpentry", "woodwork", "furniture"), "woodwork_finishing", "Woodwork Finishing", "Prepare and finish woodwork surfaces.", 40, False),
    (("painting", "wall"), "surface_preparation", "Surface Preparation", "Prepare walls and surfaces before painting.", 10, False),
    (("painting", "wall"), "interior_painting", "Interior Painting", "Perform interior wall and ceiling painting.", 20, False),
    (("painting", "wall"), "exterior_painting", "Exterior Painting", "Perform weather-appropriate exterior painting.", 30, True),
    (("painting", "wall"), "wall_repair_putty", "Wall Repair & Putty", "Repair minor wall defects and apply putty before finishing.", 40, False),
)


async def add_starter_skills(db, category_id, actor_id):
    """Add applicable starters for service groups that exist in a category.

    Existing (including retired) skills are intentionally left untouched so
    an explicit admin retirement is never silently reversed.
    """
    added = 0
    for aliases, code, name, description, order, verify in HOME_SERVICE_SKILLS:
        patterns = [f"%{alias.lower()}%" for alias in aliases]
        result = await db.execute(text("""
            WITH matched_group AS (
                SELECT sg.id
                  FROM service_groups sg
                 WHERE sg.category_id=:cid
                   AND sg.status='active'
                   AND sg.deleted_at IS NULL
                   AND (
                       lower(COALESCE(sg.code,'')) LIKE ANY(CAST(:patterns AS text[]))
                       OR lower(COALESCE(sg.slug,'')) LIKE ANY(CAST(:patterns AS text[]))
                       OR lower(sg.name) LIKE ANY(CAST(:patterns AS text[]))
                   )
                 ORDER BY sg.display_order, sg.created_at, sg.id
                 LIMIT 1
            )
            INSERT INTO category_skills
                (category_id, service_group_id, code, name, description, status,
                 requires_verification, display_order, created_by_user_id, updated_by_user_id)
            SELECT CAST(:cid AS uuid), matched_group.id, CAST(:code AS varchar),
                   CAST(:name AS varchar), CAST(:description AS varchar), 'active',
                   CAST(:verify AS boolean), CAST(:ordering AS integer),
                   CAST(:actor AS uuid), CAST(:actor AS uuid)
              FROM matched_group
             WHERE NOT EXISTS (SELECT 1 FROM category_skills
                 WHERE category_id=CAST(:cid AS uuid)
                   AND lower(name)=lower(CAST(:name AS varchar)))
            ON CONFLICT (category_id, code) DO NOTHING
        """), {"cid": str(category_id), "patterns": patterns, "code": code,
               "name": name, "description": description, "verify": verify,
               "ordering": order, "actor": str(actor_id)})
        added += result.rowcount
    return added

"""Seed a real, complete Home Services catalog (one family per appliance,
multiple job types each -- matching the Air Conditioner family already
built) plus a new "Computer & IT Services" category, using the same
service-layer classes the admin UI itself calls (not raw SQL), so every
row passes the same validation the UI enforces and shows up correctly in
the Catalog Workspace.

Run scripts/reset_home_services_catalog.py --execute FIRST on a fresh
target database. This script is NOT idempotent against partial re-runs of
itself (it does not check for existing rows before creating) -- run it
once against a clean slate. Safe to point at any environment (local or
production) since it only uses real service-layer calls; see the bottom
of this file for how to run it against production.
"""
from __future__ import annotations

import asyncio
import logging
import uuid

logging.disable(logging.INFO)

HOME_SERVICES_CATEGORY_SLUG = "home_services"
PLATFORM_ACTOR = None  # system-authored catalog content; no specific admin user


# ── Catalog data ─────────────────────────────────────────────────────────
# Each group -> list of services. Each service -> list of job types.
# job type: key (matches global job_types.key), pricing_behavior,
#   type_required/brand_required + the type/brand NAMES to map (must exist
#   in the global Types/Brands libraries), issues (name, severity),
#   questions (key, label, input_type, [options]), checklist (label, item_type, required).

def q(key, label, input_type="single_select", options=None, required=True):
    return {"key": key, "label": label, "input_type": input_type, "options": options, "required": required}


APPLIANCE_BRANDS_GENERAL = ["LG", "Samsung", "Whirlpool", "Godrej", "Haier", "Panasonic", "Voltas", "IFB", "Bosch"]

HOME_SERVICES = {
    "Appliance Repair": [
        {"name": "Microwave Oven", "job_types": [
            {"key": "repair", "pricing_behavior": "inspection_required",
             "type_required": True, "types": ["Solo", "Grill", "Convection"],
             "brand_required": True, "brands": ["LG", "Samsung", "IFB", "Panasonic", "Whirlpool", "Bosch"],
             "issues": [("Not heating", "high"), ("Turntable not rotating", "medium"), ("Sparking inside", "high"),
                        ("Display / buttons not working", "medium"), ("Door not closing properly", "low")],
             "questions": [q("microwave_type", "What type of microwave is it?"),
                           q("brand", "Which brand is it?"),
                           q("warranty_status", "Is it still under manufacturer warranty?", options=[("yes", "Yes"), ("no", "No"), ("not_sure", "Not sure")]),
                           q("issue_duration", "How long has this been happening?", options=[("today", "Started today"), ("few_days", "A few days"), ("longer", "A week or more")])],
             "checklist": [("Unplugged before opening the unit", "YES_NO", True), ("Magnetron / heating element tested", "YES_NO", True),
                           ("Turntable motor and coupler checked", "YES_NO", True), ("Door safety switch tested", "YES_NO", True),
                           ("Photo of fault / repaired part", "PHOTO", True), ("Parts replaced (if any)", "SHORT_TEXT", False),
                           ("Customer sign-off", "SIGNATURE", True)]},
            {"key": "installation", "pricing_behavior": "fixed", "type_required": False, "brand_required": False,
             "issues": [("New microwave setup", "low"), ("Wall/stand mounting needed", "low")],
             "questions": [q("mount_type", "Where will it be placed?", options=[("countertop", "Countertop"), ("wall_mount", "Wall mounted"), ("built_in", "Built-in cabinet")])],
             "checklist": [("Unit unboxed and inspected for transit damage", "YES_NO", True), ("Placed / mounted securely and levelled", "YES_NO", True),
                           ("Power point and earthing verified", "YES_NO", True), ("Test run completed", "YES_NO", True),
                           ("Photo of installed unit", "PHOTO", True), ("Customer sign-off", "SIGNATURE", True)]},
        ]},
        {"name": "Television", "job_types": [
            {"key": "repair", "pricing_behavior": "inspection_required",
             "type_required": True, "types": ["LED", "OLED", "Smart TV"],
             "brand_required": True, "brands": ["LG", "Samsung", "Sony", "Panasonic"],
             "issues": [("No display / black screen", "high"), ("No sound", "medium"), ("Lines or flickering on screen", "high"),
                        ("Not turning on", "high"), ("Smart features / apps not working", "low")],
             "questions": [q("tv_type", "What type of TV is it?"), q("brand", "Which brand is it?"),
                           q("screen_size", "What is the screen size (inches)?", "number")],
             "checklist": [("Power supply and cable checked", "YES_NO", True), ("Panel / backlight inspected", "YES_NO", True),
                           ("Main board and connections tested", "YES_NO", True), ("Photo of fault / diagnosis", "PHOTO", True),
                           ("Parts replaced (if any)", "SHORT_TEXT", False), ("Customer sign-off", "SIGNATURE", True)]},
            {"key": "installation", "pricing_behavior": "range", "type_required": False, "brand_required": False,
             "issues": [("Wall mounting", "low"), ("Stand setup", "low"), ("Cable / DTH connection setup", "low")],
             "questions": [q("mount_type", "How should it be installed?", options=[("wall_mount", "Wall mount"), ("stand", "Stand / unit")]),
                           q("screen_size", "What is the screen size (inches)?", "number")],
             "checklist": [("Wall type checked (concrete / drywall / other)", "SHORT_TEXT", True), ("Mount securely fixed and levelled", "YES_NO", True),
                           ("Cables concealed / managed", "YES_NO", True), ("Test run and channel/source setup done", "YES_NO", True),
                           ("Photo of mounted TV", "PHOTO", True), ("Customer sign-off", "SIGNATURE", True)]},
        ]},
    ],
    "Carpentry & Woodwork": [
        {"name": "Furniture Repair & Assembly", "job_types": [
            {"key": "repair", "pricing_behavior": "inspection_required", "type_required": False, "brand_required": False,
             "issues": [("Broken hinge or handle", "medium"), ("Loose joints / wobbly furniture", "medium"),
                        ("Damaged laminate / polish", "low"), ("Drawer / shutter not sliding", "medium")],
             "questions": [q("furniture_type", "What furniture needs repair?", options=[("bed", "Bed"), ("wardrobe", "Wardrobe"), ("table_chair", "Table / Chair"), ("kitchen_cabinet", "Kitchen cabinet"), ("other", "Other")]),
                           q("material", "What is it made of?", options=[("wood", "Solid wood"), ("plywood", "Plywood / MDF"), ("laminate", "Laminate board"), ("not_sure", "Not sure")])],
             "checklist": [("Damage assessed and photographed", "PHOTO", True), ("Joints/fittings repaired or replaced", "YES_NO", True),
                           ("Surface finish matched where repaired", "YES_NO", False), ("Item tested for stability", "YES_NO", True),
                           ("Customer sign-off", "SIGNATURE", True)]},
            {"key": "installation", "pricing_behavior": "range", "type_required": False, "brand_required": False,
             "issues": [("Flat-pack furniture assembly", "low"), ("Modular unit fitting", "low")],
             "questions": [q("furniture_type", "What needs to be assembled/installed?", options=[("bed", "Bed"), ("wardrobe", "Wardrobe"), ("modular_kitchen", "Modular kitchen unit"), ("other", "Other")])],
             "checklist": [("All parts and hardware verified against manual", "YES_NO", True), ("Assembled and secured to manufacturer spec", "YES_NO", True),
                           ("Levelled and wall-anchored where needed", "YES_NO", True), ("Photo of finished assembly", "PHOTO", True),
                           ("Customer sign-off", "SIGNATURE", True)]},
        ]},
    ],
    "Chimney & Hob": [
        {"name": "Kitchen Chimney", "job_types": [
            {"key": "installation", "pricing_behavior": "range",
             "type_required": True, "types": ["Wall-Mounted Chimney", "Built-In Chimney", "Island Chimney", "Straight-Line Chimney"],
             "brand_required": True, "brands": ["Faber", "Elica", "Kaff", "Glen", "Hindware"],
             "issues": [("New chimney installation", "low"), ("Ducting / venting setup", "medium")],
             "questions": [q("chimney_type", "What type of chimney is it?"), q("brand", "Which brand?"),
                           q("duct_or_ductless", "Ducted or ductless?", options=[("ducted", "Ducted (vents outside)"), ("ductless", "Ductless (recirculating filter)")])],
             "checklist": [("Mounting height and position confirmed with customer", "YES_NO", True), ("Chimney securely mounted", "YES_NO", True),
                           ("Ducting/venting routed and sealed", "YES_NO", True), ("Electrical connection tested", "YES_NO", True),
                           ("Suction / airflow test performed", "YES_NO", True), ("Photo of installed chimney", "PHOTO", True),
                           ("Customer sign-off", "SIGNATURE", True)]},
            {"key": "repair", "pricing_behavior": "inspection_required",
             "type_required": True, "types": ["Wall-Mounted Chimney", "Built-In Chimney", "Island Chimney", "Straight-Line Chimney"],
             "brand_required": True, "brands": ["Faber", "Elica", "Kaff", "Glen", "Hindware"],
             "issues": [("Low or no suction", "high"), ("Unusual noise", "medium"), ("Motor not starting", "high"), ("Lights not working", "low")],
             "questions": [q("chimney_type", "What type of chimney is it?"), q("brand", "Which brand?"),
                           q("last_service", "When was it last serviced?", options=[("never", "Never"), ("6m", "Within 6 months"), ("1y", "Within a year"), ("longer", "Longer than a year")])],
             "checklist": [("Motor and capacitor tested", "YES_NO", True), ("Filters inspected", "YES_NO", True),
                           ("Ducting checked for blockage", "YES_NO", True), ("Photo of fault / diagnosis", "PHOTO", True),
                           ("Parts replaced (if any)", "SHORT_TEXT", False), ("Customer sign-off", "SIGNATURE", True)]},
            {"key": "service", "pricing_behavior": "fixed",
             "type_required": True, "types": ["Wall-Mounted Chimney", "Built-In Chimney", "Island Chimney", "Straight-Line Chimney"],
             "brand_required": True, "brands": ["Faber", "Elica", "Kaff", "Glen", "Hindware"],
             "issues": [("Routine deep cleaning", "low"), ("Grease build-up", "medium")],
             "questions": [q("chimney_type", "What type of chimney is it?"), q("brand", "Which brand?"),
                           q("filter_type", "What type of filter does it have?", options=[("baffle", "Baffle filter"), ("mesh", "Mesh filter"), ("filterless", "Filterless / auto-clean")])],
             "checklist": [("Filters removed and degreased", "YES_NO", True), ("Motor housing and blower cleaned", "YES_NO", True),
                           ("Oil collector emptied and cleaned", "YES_NO", True), ("Suction tested after cleaning", "YES_NO", True),
                           ("Photo of cleaned unit", "PHOTO", True), ("Customer sign-off", "SIGNATURE", True)]},
        ]},
    ],
    "Electrical": [
        {"name": "Fan & Light", "job_types": [
            {"key": "installation", "pricing_behavior": "fixed", "type_required": False, "brand_required": False,
             "issues": [("New ceiling fan installation", "low"), ("New light / fixture installation", "low")],
             "questions": [q("item_type", "What needs to be installed?", options=[("ceiling_fan", "Ceiling fan"), ("light_fixture", "Light fixture"), ("exhaust_fan", "Exhaust fan")]),
                           q("point_ready", "Is the electrical point already there?", options=[("yes", "Yes"), ("no", "No, needs a new point")])],
             "checklist": [("Power isolated at the mains before starting", "YES_NO", True), ("Fixture mounted securely", "YES_NO", True),
                           ("Wiring connections tested for continuity", "YES_NO", True), ("Fan balance / light operation verified", "YES_NO", True),
                           ("Photo of installed fixture", "PHOTO", True), ("Customer sign-off", "SIGNATURE", True)]},
            {"key": "repair", "pricing_behavior": "inspection_required", "type_required": False, "brand_required": False,
             "issues": [("Fan not working", "high"), ("Fan making noise / wobbling", "medium"), ("Light flickering", "medium"), ("Light not turning on", "high")],
             "questions": [q("item_type", "What needs repair?", options=[("ceiling_fan", "Ceiling fan"), ("light_fixture", "Light fixture"), ("exhaust_fan", "Exhaust fan")])],
             "checklist": [("Power isolated at the mains before starting", "YES_NO", True), ("Capacitor / wiring tested", "YES_NO", True),
                           ("Fault identified and fixed", "YES_NO", True), ("Photo of fault / repair", "PHOTO", True),
                           ("Customer sign-off", "SIGNATURE", True)]},
        ]},
        {"name": "Switch, Socket & Wiring", "job_types": [
            {"key": "repair", "pricing_behavior": "inspection_required", "type_required": False, "brand_required": False,
             "issues": [("Switch / socket not working", "high"), ("Sparking from switchboard", "high"), ("Loose wiring", "medium"), ("Frequent tripping", "high")],
             "questions": [q("affected_points", "How many points are affected?", "number"),
                           q("issue_duration", "How long has this been happening?", options=[("today", "Started today"), ("few_days", "A few days"), ("longer", "A week or more")])],
             "checklist": [("Power isolated at the mains before starting", "YES_NO", True), ("Wiring and connections tested with meter", "YES_NO", True),
                           ("Faulty switch/socket/wiring replaced", "YES_NO", True), ("Continuity and earthing re-verified", "YES_NO", True),
                           ("Photo of completed work", "PHOTO", True), ("Customer sign-off", "SIGNATURE", True)]},
            {"key": "installation", "pricing_behavior": "range", "type_required": False, "brand_required": False,
             "issues": [("New switchboard / point installation", "low"), ("Additional socket for appliance", "low")],
             "questions": [q("points_needed", "How many new points are needed?", "number")],
             "checklist": [("Power isolated at the mains before starting", "YES_NO", True), ("New wiring run and secured", "YES_NO", True),
                           ("Switch/socket fitted and tested", "YES_NO", True), ("Earthing verified", "YES_NO", True),
                           ("Photo of completed work", "PHOTO", True), ("Customer sign-off", "SIGNATURE", True)]},
        ]},
        {"name": "MCB & Electrical Panel", "job_types": [
            {"key": "repair", "pricing_behavior": "inspection_required", "type_required": False, "brand_required": False,
             "issues": [("MCB tripping repeatedly", "high"), ("Panel overheating", "high"), ("Main switch fault", "high")],
             "questions": [q("panel_age", "Roughly how old is the electrical panel?", options=[("under_5y", "Under 5 years"), ("5_10y", "5-10 years"), ("over_10y", "Over 10 years"), ("not_sure", "Not sure")])],
             "checklist": [("Power isolated at the mains before starting", "YES_NO", True), ("Load and connections inspected", "YES_NO", True),
                           ("Faulty MCB/component replaced", "YES_NO", True), ("Panel tested under load after repair", "YES_NO", True),
                           ("Photo of completed work", "PHOTO", True), ("Customer sign-off", "SIGNATURE", True)]},
            {"key": "installation", "pricing_behavior": "custom_quote", "type_required": False, "brand_required": False,
             "issues": [("New MCB / panel upgrade", "medium")],
             "questions": [q("reason", "Why is a new panel/MCB needed?", options=[("upgrade", "Capacity upgrade"), ("new_construction", "New construction"), ("damaged", "Existing one damaged")])],
             "checklist": [("Load requirement assessed", "YES_NO", True), ("Panel/MCB installed to code", "YES_NO", True),
                           ("Earthing and load-tested", "YES_NO", True), ("Photo of installed panel", "PHOTO", True),
                           ("Customer sign-off", "SIGNATURE", True)]},
        ]},
    ],
    "Geyser & Water Heater": [
        {"name": "Geyser / Water Heater", "job_types": [
            {"key": "installation", "pricing_behavior": "range",
             "type_required": True, "types": ["Instant Geyser", "Storage Geyser", "Gas Geyser", "Solar Water Heater"],
             "brand_required": True, "brands": ["AO Smith", "Racold", "Venus", "Bajaj", "Havells", "V-Guard"],
             "issues": [("New geyser installation", "low"), ("Pipe / valve fitting", "medium")],
             "questions": [q("geyser_type", "What type of geyser is it?"), q("brand", "Which brand?"),
                           q("capacity", "What is the capacity (litres)?", "number", required=False)],
             "checklist": [("Mounting location and bracket verified", "YES_NO", True), ("Inlet/outlet pipes and valves fitted", "YES_NO", True),
                           ("Electrical / gas connection tested", "YES_NO", True), ("Pressure relief valve checked", "YES_NO", True),
                           ("Photo of installed unit", "PHOTO", True), ("Customer sign-off", "SIGNATURE", True)]},
            {"key": "repair", "pricing_behavior": "inspection_required",
             "type_required": True, "types": ["Instant Geyser", "Storage Geyser", "Gas Geyser", "Solar Water Heater"],
             "brand_required": True, "brands": ["AO Smith", "Racold", "Venus", "Bajaj", "Havells", "V-Guard"],
             "issues": [("No hot water", "high"), ("Water leaking", "high"), ("Tripping the electrical circuit", "high"), ("Unusual noise", "medium")],
             "questions": [q("geyser_type", "What type of geyser is it?"), q("brand", "Which brand?")],
             "checklist": [("Power/gas isolated before starting", "YES_NO", True), ("Heating element / thermostat tested", "YES_NO", True),
                           ("Tank and valves checked for leaks", "YES_NO", True), ("Photo of fault / diagnosis", "PHOTO", True),
                           ("Parts replaced (if any)", "SHORT_TEXT", False), ("Customer sign-off", "SIGNATURE", True)]},
            {"key": "service", "pricing_behavior": "fixed",
             "type_required": True, "types": ["Instant Geyser", "Storage Geyser", "Gas Geyser", "Solar Water Heater"],
             "brand_required": True, "brands": ["AO Smith", "Racold", "Venus", "Bajaj", "Havells", "V-Guard"],
             "issues": [("Descaling / anode rod service", "low"), ("Routine maintenance", "low")],
             "questions": [q("geyser_type", "What type of geyser is it?"), q("last_service", "When was it last serviced?", options=[("never", "Never"), ("1y", "Within a year"), ("longer", "Longer than a year")])],
             "checklist": [("Tank descaled", "YES_NO", True), ("Anode rod inspected / replaced", "YES_NO", False),
                           ("Heating element cleaned", "YES_NO", True), ("Safety valve tested", "YES_NO", True),
                           ("Photo of serviced unit", "PHOTO", True), ("Customer sign-off", "SIGNATURE", True)]},
        ]},
    ],
    "Home Security": [
        {"name": "CCTV Camera", "job_types": [
            {"key": "installation", "pricing_behavior": "custom_quote", "type_required": False, "brand_required": False,
             "issues": [("New CCTV setup", "low"), ("Additional camera point", "low")],
             "questions": [q("camera_count", "How many cameras are needed?", "number"),
                           q("location", "Indoor, outdoor, or both?", options=[("indoor", "Indoor"), ("outdoor", "Outdoor"), ("both", "Both")]),
                           q("recording", "Local storage (DVR/NVR) or cloud recording?", options=[("local", "Local (DVR/NVR)"), ("cloud", "Cloud"), ("not_sure", "Not sure")])],
             "checklist": [("Camera positions confirmed with customer", "YES_NO", True), ("Cameras mounted and cabled", "YES_NO", True),
                           ("DVR/NVR configured and recording verified", "YES_NO", True), ("Remote/mobile access set up", "YES_NO", False),
                           ("Photo of installed setup", "PHOTO", True), ("Customer sign-off", "SIGNATURE", True)]},
            {"key": "repair", "pricing_behavior": "inspection_required", "type_required": False, "brand_required": False,
             "issues": [("Camera not recording", "high"), ("No video feed", "high"), ("Night vision not working", "medium"), ("DVR/NVR not booting", "high")],
             "questions": [q("camera_count", "How many cameras are affected?", "number")],
             "checklist": [("Power and cabling tested", "YES_NO", True), ("Camera and DVR/NVR diagnosed", "YES_NO", True),
                           ("Fault fixed and feed verified", "YES_NO", True), ("Photo of fault / diagnosis", "PHOTO", True),
                           ("Customer sign-off", "SIGNATURE", True)]},
        ]},
        {"name": "Video Door Bell & Smart Lock", "job_types": [
            {"key": "installation", "pricing_behavior": "range", "type_required": False, "brand_required": False,
             "issues": [("New video doorbell setup", "low"), ("New smart lock installation", "low")],
             "questions": [q("device_type", "What is being installed?", options=[("video_doorbell", "Video doorbell"), ("smart_lock", "Smart lock")]),
                           q("wifi_available", "Is WiFi available at the door?", options=[("yes", "Yes"), ("no", "No")])],
             "checklist": [("Door/frame condition checked", "YES_NO", True), ("Device mounted and wired/powered", "YES_NO", True),
                           ("App paired and connectivity tested", "YES_NO", True), ("Photo of installed device", "PHOTO", True),
                           ("Customer sign-off", "SIGNATURE", True)]},
            {"key": "repair", "pricing_behavior": "inspection_required", "type_required": False, "brand_required": False,
             "issues": [("Not connecting to app", "medium"), ("Battery / power issue", "medium"), ("Lock jamming", "high")],
             "questions": [q("device_type", "What needs repair?", options=[("video_doorbell", "Video doorbell"), ("smart_lock", "Smart lock")])],
             "checklist": [("Device and connectivity diagnosed", "YES_NO", True), ("Fault fixed / part replaced", "YES_NO", True),
                           ("Function tested after repair", "YES_NO", True), ("Customer sign-off", "SIGNATURE", True)]},
        ]},
    ],
    "Painting & Walls": [
        {"name": "Wall Painting", "job_types": [
            {"key": "service", "pricing_behavior": "custom_quote", "type_required": False, "brand_required": False,
             "issues": [("Interior wall painting", "low"), ("Exterior wall painting", "low"), ("Wall crack / seepage before painting", "medium"), ("Ceiling painting", "low")],
             "questions": [q("area_type", "Interior or exterior?", options=[("interior", "Interior"), ("exterior", "Exterior"), ("both", "Both")]),
                           q("room_count", "How many rooms / how much area (sq ft)?", "text"),
                           q("paint_provided", "Will you provide the paint or should we?", options=[("customer", "I'll provide it"), ("provider", "Provider to supply")])],
             "checklist": [("Surface prepared (cleaned, cracks filled, sanded)", "YES_NO", True), ("Furniture / floor covered and protected", "YES_NO", True),
                           ("Primer coat applied where needed", "YES_NO", False), ("Final coats applied evenly", "YES_NO", True),
                           ("Site cleaned after work", "YES_NO", True), ("Photo of finished area", "PHOTO", True), ("Customer sign-off", "SIGNATURE", True)]},
        ]},
        {"name": "Waterproofing", "job_types": [
            {"key": "service", "pricing_behavior": "custom_quote", "type_required": False, "brand_required": False,
             "issues": [("Terrace / roof leakage", "high"), ("Wall seepage", "medium"), ("Bathroom leakage", "high")],
             "questions": [q("leak_location", "Where is the leakage?", options=[("terrace", "Terrace / roof"), ("wall", "Wall"), ("bathroom", "Bathroom"), ("basement", "Basement")]),
                           q("leak_duration", "How long has this been happening?", options=[("recent", "Recently started"), ("ongoing", "Ongoing for months"), ("seasonal", "Only in monsoon")])],
             "checklist": [("Leakage source identified", "YES_NO", True), ("Surface cleaned and cracks treated", "YES_NO", True),
                           ("Waterproofing coating/membrane applied", "YES_NO", True), ("Water test performed after treatment", "YES_NO", True),
                           ("Photo of treated area", "PHOTO", True), ("Customer sign-off", "SIGNATURE", True)]},
        ]},
    ],
    "Pest Control": [
        {"name": "Pest Control", "job_types": [
            {"key": "service", "pricing_behavior": "range", "type_required": False, "brand_required": False,
             "issues": [("General pest control (cockroach, ants)", "medium"), ("Termite treatment", "high"), ("Bed bug treatment", "high"), ("Rodent control", "medium"), ("Mosquito control", "low")],
             "questions": [q("pest_type", "What pest issue are you facing?", options=[("general", "Cockroach / ants (general)"), ("termite", "Termites"), ("bedbug", "Bed bugs"), ("rodent", "Rodents"), ("mosquito", "Mosquitoes")]),
                           q("property_size", "Approximate area (BHK / sq ft)?", "text"),
                           q("infestation_level", "How severe is the infestation?", options=[("mild", "Mild"), ("moderate", "Moderate"), ("severe", "Severe")])],
             "checklist": [("Affected areas inspected", "YES_NO", True), ("Treatment plan explained to customer", "YES_NO", True),
                           ("Safe chemical application per pest type", "YES_NO", True), ("Pets/food items protected during treatment", "YES_NO", True),
                           ("Post-treatment safety instructions given", "YES_NO", True), ("Photo of treated area", "PHOTO", False),
                           ("Customer sign-off", "SIGNATURE", True)]},
        ]},
    ],
    "Plumbing": [
        {"name": "Plumbing", "job_types": [
            {"key": "repair", "pricing_behavior": "inspection_required", "type_required": False, "brand_required": False,
             "issues": [("Leaking pipe or joint", "high"), ("Clogged drain", "medium"), ("Dripping tap", "low"), ("Low water pressure", "medium"), ("Toilet flush issue", "medium")],
             "questions": [q("issue_location", "Where is the issue?", options=[("kitchen", "Kitchen"), ("bathroom", "Bathroom"), ("main_line", "Main line"), ("other", "Other")]),
                           q("issue_duration", "How long has this been happening?", options=[("today", "Started today"), ("few_days", "A few days"), ("longer", "A week or more")])],
             "checklist": [("Water supply isolated before starting", "YES_NO", True), ("Leak / blockage source identified", "YES_NO", True),
                           ("Fault fixed and leak-tested", "YES_NO", True), ("Photo of completed repair", "PHOTO", True),
                           ("Parts replaced (if any)", "SHORT_TEXT", False), ("Customer sign-off", "SIGNATURE", True)]},
            {"key": "installation", "pricing_behavior": "range", "type_required": False, "brand_required": False,
             "issues": [("New tap / fixture installation", "low"), ("New pipeline for appliance", "medium")],
             "questions": [q("fixture_type", "What needs to be installed?", options=[("tap", "Tap / faucet"), ("wash_basin", "Wash basin"), ("commode", "Commode"), ("other", "Other")])],
             "checklist": [("Water supply isolated before starting", "YES_NO", True), ("Fixture fitted and sealed", "YES_NO", True),
                           ("Leak-tested under running water", "YES_NO", True), ("Photo of installed fixture", "PHOTO", True),
                           ("Customer sign-off", "SIGNATURE", True)]},
            {"key": "service", "pricing_behavior": "fixed", "type_required": False, "brand_required": False,
             "issues": [("Water tank cleaning", "low")],
             "questions": [q("tank_capacity", "Approximate tank capacity (litres)?", "number", required=False)],
             "checklist": [("Tank drained safely", "YES_NO", True), ("Interior scrubbed and sediment removed", "YES_NO", True),
                           ("Disinfected and rinsed thoroughly", "YES_NO", True), ("Refilled and checked for leaks", "YES_NO", True),
                           ("Photo of cleaned tank", "PHOTO", True), ("Customer sign-off", "SIGNATURE", True)]},
        ]},
    ],
    "Refrigerator": [
        {"name": "Refrigerator", "job_types": [
            {"key": "repair", "pricing_behavior": "inspection_required",
             "type_required": True, "types": ["Single Door", "Double Door", "Side-by-Side", "French Door"],
             "brand_required": True, "brands": ["LG", "Samsung", "Whirlpool", "Godrej", "Haier", "Panasonic", "Voltas"],
             "issues": [("Not cooling", "high"), ("Excess frost / ice build-up", "medium"), ("Water leakage", "medium"), ("Unusual noise", "low"), ("Door not sealing", "medium")],
             "questions": [q("fridge_type", "What type of refrigerator is it?"), q("brand", "Which brand?")],
             "checklist": [("Power supply and thermostat tested", "YES_NO", True), ("Compressor / gas level checked", "YES_NO", True),
                           ("Door seal inspected", "YES_NO", True), ("Photo of fault / diagnosis", "PHOTO", True),
                           ("Parts replaced (if any)", "SHORT_TEXT", False), ("Customer sign-off", "SIGNATURE", True)]},
            {"key": "service", "pricing_behavior": "fixed",
             "type_required": True, "types": ["Single Door", "Double Door", "Side-by-Side", "French Door"],
             "brand_required": True, "brands": ["LG", "Samsung", "Whirlpool", "Godrej", "Haier", "Panasonic", "Voltas"],
             "issues": [("Preventive maintenance / gas top-up check", "low")],
             "questions": [q("fridge_type", "What type of refrigerator is it?"), q("last_service", "When was it last serviced?", options=[("never", "Never"), ("1y", "Within a year"), ("longer", "Longer than a year")])],
             "checklist": [("Coils and condenser cleaned", "YES_NO", True), ("Door seals and gaskets checked", "YES_NO", True),
                           ("Cooling performance verified", "YES_NO", True), ("Photo of serviced unit", "PHOTO", True),
                           ("Customer sign-off", "SIGNATURE", True)]},
        ]},
    ],
    "RO & Water Purifier": [
        {"name": "RO Water Purifier", "job_types": [
            {"key": "installation", "pricing_behavior": "range",
             "type_required": True, "types": ["RO + UV", "RO + UV + UF", "UV Purifier", "Gravity Purifier"],
             "brand_required": True, "brands": ["Kent", "Aquaguard", "Pureit", "Livpure", "Havells"],
             "issues": [("New RO installation", "low")],
             "questions": [q("purifier_type", "What type of purifier is it?"), q("brand", "Which brand?"),
                           q("water_source", "What is the water source?", options=[("municipal", "Municipal supply"), ("borewell", "Borewell"), ("tanker", "Tanker")])],
             "checklist": [("Mounting location and water inlet confirmed", "YES_NO", True), ("Unit mounted and plumbed in", "YES_NO", True),
                           ("Filters/membrane fitted correctly", "YES_NO", True), ("TDS / output tested after install", "YES_NO", True),
                           ("Photo of installed unit", "PHOTO", True), ("Customer sign-off", "SIGNATURE", True)]},
            {"key": "repair", "pricing_behavior": "inspection_required",
             "type_required": True, "types": ["RO + UV", "RO + UV + UF", "UV Purifier", "Gravity Purifier"],
             "brand_required": True, "brands": ["Kent", "Aquaguard", "Pureit", "Livpure", "Havells"],
             "issues": [("No water output", "high"), ("Water leakage", "medium"), ("Bad taste / odour", "medium"), ("Continuous pump running", "high")],
             "questions": [q("purifier_type", "What type of purifier is it?"), q("brand", "Which brand?")],
             "checklist": [("Power and pump tested", "YES_NO", True), ("Membrane / filters inspected", "YES_NO", True),
                           ("Leak points checked and sealed", "YES_NO", True), ("TDS tested after repair", "YES_NO", True),
                           ("Photo of fault / diagnosis", "PHOTO", True), ("Parts replaced (if any)", "SHORT_TEXT", False),
                           ("Customer sign-off", "SIGNATURE", True)]},
            {"key": "service", "pricing_behavior": "fixed",
             "type_required": True, "types": ["RO + UV", "RO + UV + UF", "UV Purifier", "Gravity Purifier"],
             "brand_required": True, "brands": ["Kent", "Aquaguard", "Pureit", "Livpure", "Havells"],
             "issues": [("Filter / membrane change", "low")],
             "questions": [q("purifier_type", "What type of purifier is it?"), q("last_filter_change", "When were filters last changed?", options=[("never", "Never"), ("6m", "Within 6 months"), ("1y", "Within a year"), ("longer", "Longer than a year")])],
             "checklist": [("Filters/membrane replaced as due", "YES_NO", True), ("Unit sanitized", "YES_NO", True),
                           ("TDS and output tested after service", "YES_NO", True), ("Photo of serviced unit", "PHOTO", True),
                           ("Customer sign-off", "SIGNATURE", True)]},
        ]},
    ],
    "Washing Machine": [
        {"name": "Washing Machine", "job_types": [
            {"key": "installation", "pricing_behavior": "fixed",
             "type_required": True, "types": ["Top Load", "Front Load", "Semi-Automatic"],
             "brand_required": True, "brands": ["LG", "Samsung", "Whirlpool", "IFB", "Bosch", "Haier"],
             "issues": [("New machine installation", "low")],
             "questions": [q("machine_type", "What type of washing machine is it?"), q("brand", "Which brand?")],
             "checklist": [("Levelled and transit bolts removed", "YES_NO", True), ("Inlet/outlet hoses connected and tested", "YES_NO", True),
                           ("Power point and earthing verified", "YES_NO", True), ("Test wash cycle run", "YES_NO", True),
                           ("Photo of installed unit", "PHOTO", True), ("Customer sign-off", "SIGNATURE", True)]},
            {"key": "repair", "pricing_behavior": "inspection_required",
             "type_required": True, "types": ["Top Load", "Front Load", "Semi-Automatic"],
             "brand_required": True, "brands": ["LG", "Samsung", "Whirlpool", "IFB", "Bosch", "Haier"],
             "issues": [("Not spinning / draining", "high"), ("Water leakage", "high"), ("Excess noise / vibration", "medium"), ("Not powering on", "high"), ("Door / lid lock issue", "medium")],
             "questions": [q("machine_type", "What type of washing machine is it?"), q("brand", "Which brand?")],
             "checklist": [("Power isolated before starting", "YES_NO", True), ("Motor / drum / pump tested", "YES_NO", True),
                           ("Hoses and seals checked for leaks", "YES_NO", True), ("Photo of fault / diagnosis", "PHOTO", True),
                           ("Parts replaced (if any)", "SHORT_TEXT", False), ("Customer sign-off", "SIGNATURE", True)]},
            {"key": "service", "pricing_behavior": "fixed",
             "type_required": True, "types": ["Top Load", "Front Load", "Semi-Automatic"],
             "brand_required": True, "brands": ["LG", "Samsung", "Whirlpool", "IFB", "Bosch", "Haier"],
             "issues": [("Drum deep cleaning", "low"), ("Odour removal", "low")],
             "questions": [q("machine_type", "What type of washing machine is it?")],
             "checklist": [("Drum and gasket deep-cleaned", "YES_NO", True), ("Detergent drawer cleaned", "YES_NO", True),
                           ("Filter cleared of debris", "YES_NO", True), ("Test cycle run after cleaning", "YES_NO", True),
                           ("Photo of cleaned unit", "PHOTO", True), ("Customer sign-off", "SIGNATURE", True)]},
        ]},
    ],
}

COMPUTER_SERVICES = {
    "Computer & Laptop Repair": [
        {"name": "Desktop Computer", "job_types": [
            {"key": "installation", "pricing_behavior": "range", "type_required": False, "brand_required": False,
             "issues": [("New PC assembly / CPU installation", "low"), ("Component upgrade (RAM / SSD / GPU)", "medium"), ("New setup at customer location", "low")],
             "questions": [q("build_type", "What kind of setup is this?", options=[("new_build", "New PC assembly"), ("upgrade", "Component upgrade"), ("relocate", "Relocate / re-setup existing PC")]),
                           q("components", "Which components need installing/upgrading?", "text", required=False)],
             "checklist": [("Static-safe handling followed", "YES_NO", True), ("Components installed and seated correctly", "YES_NO", True),
                           ("Cabling and airflow checked", "YES_NO", True), ("System boots and POSTs successfully", "YES_NO", True),
                           ("Photo of completed build", "PHOTO", True), ("Customer sign-off", "SIGNATURE", True)]},
            {"key": "repair", "pricing_behavior": "inspection_required", "type_required": False, "brand_required": False,
             "issues": [("Not powering on", "high"), ("Overheating / shutting down", "medium"), ("Blue screen / crashes", "high"), ("No display output", "high")],
             "questions": [q("symptom_when", "When does the issue happen?", options=[("startup", "At startup"), ("during_use", "During use"), ("random", "Randomly")])],
             "checklist": [("Power supply and connections tested", "YES_NO", True), ("Hardware diagnostics run", "YES_NO", True),
                           ("Fault identified and fixed / part replaced", "YES_NO", True), ("System stability verified after fix", "YES_NO", True),
                           ("Photo of diagnosis / fix", "PHOTO", False), ("Customer sign-off", "SIGNATURE", True)]},
            {"key": "service", "pricing_behavior": "fixed", "type_required": False, "brand_required": False,
             "issues": [("Windows installation / reinstallation", "medium"), ("Software setup & driver installation", "low"), ("Virus / malware removal", "medium"), ("Slow performance clean-up", "low")],
             "questions": [q("service_needed", "What do you need done?", options=[("windows_install", "Windows installation"), ("software_setup", "Software / driver setup"), ("virus_removal", "Virus / malware removal"), ("performance", "Speed up a slow PC")]),
                           q("data_backup", "Does existing data need to be backed up first?", options=[("yes", "Yes"), ("no", "No"), ("not_sure", "Not sure")])],
             "checklist": [("Existing data backed up if requested", "YES_NO", False), ("OS / software installed and activated", "YES_NO", True),
                           ("Drivers and updates installed", "YES_NO", True), ("Antivirus / security software configured", "YES_NO", False),
                           ("System tested and handed back working", "YES_NO", True), ("Customer sign-off", "SIGNATURE", True)]},
        ]},
        {"name": "Laptop", "job_types": [
            {"key": "repair", "pricing_behavior": "inspection_required", "type_required": False, "brand_required": False,
             "issues": [("Not powering on", "high"), ("Screen damage / display issue", "high"), ("Battery not charging", "medium"), ("Keyboard / trackpad issue", "medium"), ("Overheating", "medium")],
             "questions": [q("laptop_brand", "What is the laptop brand?", "text", required=False),
                           q("warranty_status", "Is it under manufacturer warranty?", options=[("yes", "Yes"), ("no", "No"), ("not_sure", "Not sure")])],
             "checklist": [("Hardware diagnostics run", "YES_NO", True), ("Fault identified and fixed / part replaced", "YES_NO", True),
                           ("Battery and charging verified", "YES_NO", True), ("Photo of diagnosis / fix", "PHOTO", False),
                           ("Customer sign-off", "SIGNATURE", True)]},
            {"key": "service", "pricing_behavior": "fixed", "type_required": False, "brand_required": False,
             "issues": [("Windows / OS installation", "medium"), ("Software setup", "low"), ("Virus / malware removal", "medium")],
             "questions": [q("service_needed", "What do you need done?", options=[("windows_install", "Windows / OS installation"), ("software_setup", "Software setup"), ("virus_removal", "Virus / malware removal")]),
                           q("data_backup", "Does existing data need to be backed up first?", options=[("yes", "Yes"), ("no", "No"), ("not_sure", "Not sure")])],
             "checklist": [("Existing data backed up if requested", "YES_NO", False), ("OS / software installed and activated", "YES_NO", True),
                           ("Drivers and updates installed", "YES_NO", True), ("System tested and handed back working", "YES_NO", True),
                           ("Customer sign-off", "SIGNATURE", True)]},
        ]},
    ],
    "Networking & Peripherals": [
        {"name": "Printer", "job_types": [
            {"key": "installation", "pricing_behavior": "fixed", "type_required": False, "brand_required": False,
             "issues": [("New printer setup", "low"), ("Network / WiFi printer setup", "low")],
             "questions": [q("connection_type", "How should it connect?", options=[("usb", "USB (direct)"), ("wifi", "WiFi / network")])],
             "checklist": [("Printer unboxed and cartridges/toner fitted", "YES_NO", True), ("Connected and drivers installed", "YES_NO", True),
                           ("Test print completed", "YES_NO", True), ("Customer sign-off", "SIGNATURE", True)]},
            {"key": "repair", "pricing_behavior": "inspection_required", "type_required": False, "brand_required": False,
             "issues": [("Paper jam", "medium"), ("Not printing / offline", "high"), ("Print quality poor / streaky", "medium"), ("Not connecting to network", "medium")],
             "questions": [q("connection_type", "How is it connected?", options=[("usb", "USB (direct)"), ("wifi", "WiFi / network")])],
             "checklist": [("Hardware and connection diagnosed", "YES_NO", True), ("Fault fixed / part cleaned or replaced", "YES_NO", True),
                           ("Test print completed after fix", "YES_NO", True), ("Customer sign-off", "SIGNATURE", True)]},
        ]},
        {"name": "WiFi Router & Networking", "job_types": [
            {"key": "installation", "pricing_behavior": "fixed", "type_required": False, "brand_required": False,
             "issues": [("New router setup", "low"), ("Home network / WiFi extender setup", "low")],
             "questions": [q("coverage_area", "How large is the area to cover?", options=[("1bhk", "1 BHK"), ("2_3bhk", "2-3 BHK"), ("villa_large", "Villa / large home")]),
                           q("isp_provided", "Is this the ISP's router or a new one?", options=[("isp", "ISP-provided"), ("new", "New router")])],
             "checklist": [("Router configured with secure network name/password", "YES_NO", True), ("Placement optimized for coverage", "YES_NO", True),
                           ("Connected devices tested for signal", "YES_NO", True), ("Customer sign-off", "SIGNATURE", True)]},
            {"key": "repair", "pricing_behavior": "inspection_required", "type_required": False, "brand_required": False,
             "issues": [("No internet connectivity", "high"), ("Weak WiFi signal / dead zones", "medium"), ("Frequent disconnections", "medium")],
             "questions": [q("issue_scope", "Is the issue everywhere or in specific areas?", options=[("everywhere", "Everywhere"), ("specific_area", "Specific area / room")])],
             "checklist": [("Router and connections diagnosed", "YES_NO", True), ("Firmware / configuration checked and fixed", "YES_NO", True),
                           ("Signal tested after fix", "YES_NO", True), ("Customer sign-off", "SIGNATURE", True)]},
        ]},
    ],
}


# ── Driver ───────────────────────────────────────────────────────────────

async def build_category(db, name: str, slug: str, description: str):
    from sqlalchemy import select
    from app.engines.admin_catalog.models import ServiceCategory
    existing = (await db.execute(select(ServiceCategory).where(ServiceCategory.slug == slug))).scalar_one_or_none()
    if existing:
        return existing
    cat = ServiceCategory(name=name, slug=slug, description=description, is_active=True)
    db.add(cat)
    await db.flush()
    return cat


async def ensure_group(admin_svc, category_id, name: str):
    from sqlalchemy import select
    from app.engines.admin_catalog.models import ServiceGroup
    existing = (await admin_svc.db.execute(
        select(ServiceGroup).where(ServiceGroup.category_id == category_id, ServiceGroup.name == name)
    )).scalar_one_or_none()
    if existing:
        return existing.id
    result = await admin_svc.create_service_group({"category_id": str(category_id), "name": name})
    return uuid.UUID(result["id"])


async def build_job_type(db, admin_svc, jt_svc, question_svc, checklist_svc_module,
                          dim_svc, master_service_id, jt_spec, type_dim_id, brand_dim_id,
                          type_name_to_id, brand_name_to_id):
    from app.engines.checklist_catalog import constants as c

    link = await jt_svc.add_job_type_to_service(master_service_id, {"job_type_id": str(jt_spec["_job_type_id"])})
    link_id = uuid.UUID(link["id"])
    job_type_id = uuid.UUID(link["job_type_id"])

    await jt_svc.set_workflow(master_service_id, job_type_id, {"pricing_behavior": jt_spec["pricing_behavior"]})

    from app.exceptions import ServiceOSException as _SOE
    if jt_spec.get("type_required"):
        await dim_svc.set_service_job_dimension(master_service_id, job_type_id, type_dim_id, {"enabled": True, "required": True, "ask_customer": True})
        for t in jt_spec["types"]:
            tid = type_name_to_id.get(t)
            if tid:
                try:
                    await admin_svc.map_service_type(master_service_id, {"service_type_id": str(tid), "is_required": False})
                except _SOE as exc:
                    # Type/brand mappings are service-wide, not per-job-type --
                    # a later job type on the same service re-declaring an
                    # already-mapped type is expected, not an error.
                    if exc.error_code != "MAPPING_DUPLICATE":
                        raise
    if jt_spec.get("brand_required"):
        await dim_svc.set_service_job_dimension(master_service_id, job_type_id, brand_dim_id, {"enabled": True, "required": True, "ask_customer": True})
        for b in jt_spec["brands"]:
            bid = brand_name_to_id.get(b)
            if bid:
                try:
                    await admin_svc.map_service_brand(master_service_id, {"brand_id": str(bid), "is_required": False})
                except _SOE as exc:
                    if exc.error_code != "MAPPING_DUPLICATE":
                        raise

    import re
    from sqlalchemy import select as _select
    from app.engines.admin_catalog.models import MasterIssueType
    for name, severity in jt_spec["issues"]:
        slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
        existing_issue = (await db.execute(_select(MasterIssueType).where(MasterIssueType.slug == slug))).scalar_one_or_none()
        if existing_issue:
            issue_id = str(existing_issue.id)
        else:
            issue = await admin_svc.opt_svc.create_issue_type({
                "name": name, "severity": severity, "customer_visible": True,
            })
            issue_id = issue["id"]
        await admin_svc.opt_svc.add_service_issue_mapping(master_service_id, {
            "issue_type_id": issue_id, "job_type_id": str(job_type_id), "customer_visible": True,
        })

    for qspec in jt_spec["questions"]:
        has_options = bool(qspec.get("options"))
        created = await question_svc.create_question({
            "master_service_id": str(master_service_id), "job_type_id": str(job_type_id),
            "question_key": qspec["key"], "label": qspec["label"],
            "input_type": qspec["input_type"] if not has_options else "single_select",
            "answer_source": "static" if has_options else "free",
            "required": qspec.get("required", True), "customer_visible": True,
        })
        if has_options:
            for i, (code, label) in enumerate(qspec["options"]):
                await question_svc.add_option(uuid.UUID(created["id"]), {"code": code, "label": label, "display_order": i})

    template = await checklist_svc_module.create_template(
        db, name=f"{jt_spec['_service_name']} {jt_spec['_job_type_label']} - Job Completion",
        code=f"{jt_spec['_code_prefix']}_{jt_spec['key'].upper()}_COMPLETION",
        description=None, purpose=c.PURPOSE_COMPLETION, owner_scope=c.OWNER_SCOPE_PLATFORM,
        tenant_id=None, created_by_user_id=None,
    )
    version = await checklist_svc_module.get_draft_version(db, template.id)
    section = await checklist_svc_module.add_section(db, version, "Job Completion", 0)
    for i, (label, item_type, required) in enumerate(jt_spec["checklist"]):
        await checklist_svc_module.add_item(db, section, version, label=label, item_type=item_type,
                                            is_required=required, display_order=i)
    await checklist_svc_module.publish_version(db, version, published_by=None, change_summary="Initial seed")
    await checklist_svc_module.create_mapping(
        db, master_service_job_type_id=link_id, service_job_workflow_id=None,
        checklist_template_version_id=version.id, phase=c.PURPOSE_EXECUTION, usage=c.USAGE_REQUIRED,
        actor=c.ACTOR_TECHNICIAN, completion_gate=c.GATE_BEFORE_JOB_COMPLETION,
        condition_rules=None, display_order=0, created_by=None,
    )
    await db.commit()


async def build_service(db, admin_svc, jt_svc, question_svc, checklist_svc_module, dim_svc,
                        category_id, group_id, service_name, job_type_specs,
                        job_type_key_to_id, type_dim_id, brand_dim_id, type_name_to_id, brand_name_to_id):
    from sqlalchemy import select as _select
    from app.engines.admin_catalog.models import MasterService
    existing = (await db.execute(_select(MasterService).where(
        MasterService.service_group_id == group_id, MasterService.service_name == service_name,
    ))).scalar_one_or_none()
    if existing:
        print(f"  = {service_name} already exists, skipping")
        return existing.id

    result = await admin_svc.create_master_service_canonical({
        "service_name": service_name, "category_id": str(category_id), "service_group_id": str(group_id),
    })
    master_service_id = uuid.UUID(result["service_id"])
    import re as _re
    # Full-name slug, not first-letter initials -- avoids collisions between
    # differently-named services that happen to share initials (checklist
    # template codes are globally unique).
    code_prefix = _re.sub(r"[^A-Z0-9]+", "_", service_name.upper()).strip("_")[:40] or "SVC"
    for jt_spec in job_type_specs:
        jt_spec = dict(jt_spec)
        jt_spec["_job_type_id"] = job_type_key_to_id[jt_spec["key"]]
        jt_spec["_service_name"] = service_name
        jt_spec["_job_type_label"] = jt_spec["key"].capitalize()
        jt_spec["_code_prefix"] = code_prefix
        await build_job_type(db, admin_svc, jt_svc, question_svc, checklist_svc_module, dim_svc,
                             master_service_id, jt_spec, type_dim_id, brand_dim_id,
                             type_name_to_id, brand_name_to_id)
    print(f"  + {service_name} ({len(job_type_specs)} job type(s))")
    return master_service_id


async def run():
    from sqlalchemy import select
    from app.database import init_db, get_session_factory
    from app.engines.admin_catalog.service import AdminCatalogService
    from app.engines.admin_catalog.service_option_service import ServiceOptionService
    from app.engines.admin_catalog.job_type_blueprint_service import JobTypeBlueprintService
    from app.engines.admin_catalog.question_service import CatalogQuestionService
    from app.engines.admin_catalog.dimension_service import CatalogDimensionService
    from app.engines.admin_catalog.models import ServiceCategory, ServiceType, Brand, CatalogDimension, JobTypeDefinition
    from app.engines.checklist_catalog import service as checklist_svc_module

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        admin_svc = AdminCatalogService(db=db, actor_id=None)
        admin_svc.opt_svc = ServiceOptionService(db=db, actor_id=None, actor_role="super_admin", request_id="seed-script")
        jt_svc = JobTypeBlueprintService(db=db)
        question_svc = CatalogQuestionService(db=db)
        dim_svc = CatalogDimensionService(db=db)

        type_dim_id = (await db.execute(select(CatalogDimension.id).where(CatalogDimension.legacy_source == "service_types"))).scalar_one()
        brand_dim_id = (await db.execute(select(CatalogDimension.id).where(CatalogDimension.legacy_source == "brands"))).scalar_one()
        type_name_to_id = dict((await db.execute(select(ServiceType.name, ServiceType.id))).all())
        brand_name_to_id = dict((await db.execute(select(Brand.name, Brand.id))).all())
        job_type_key_to_id = dict((await db.execute(select(JobTypeDefinition.key, JobTypeDefinition.id))).all())

        home_cat = (await db.execute(select(ServiceCategory).where(ServiceCategory.slug == HOME_SERVICES_CATEGORY_SLUG))).scalar_one()
        print(f"Home Services category: {home_cat.id}")
        for group_name, services in HOME_SERVICES.items():
            group_id = await ensure_group(admin_svc, home_cat.id, group_name)
            print(f"Group: {group_name}")
            for svc_spec in services:
                try:
                    await build_service(db, admin_svc, jt_svc, question_svc, checklist_svc_module, dim_svc,
                                        home_cat.id, group_id, svc_spec["name"], svc_spec["job_types"],
                                        job_type_key_to_id, type_dim_id, brand_dim_id, type_name_to_id, brand_name_to_id)
                except Exception as exc:
                    await db.rollback()
                    print(f"  ! FAILED: {svc_spec['name']}: {exc}")

        computer_cat = await build_category(db, "Computer & IT Services", "computer_it_services",
            "Computer, laptop, printer and home networking repair, installation and setup.")
        await db.flush()
        print(f"\nComputer & IT Services category: {computer_cat.id}")
        for group_name, services in COMPUTER_SERVICES.items():
            group_id = await ensure_group(admin_svc, computer_cat.id, group_name)
            print(f"Group: {group_name}")
            for svc_spec in services:
                try:
                    await build_service(db, admin_svc, jt_svc, question_svc, checklist_svc_module, dim_svc,
                                        computer_cat.id, group_id, svc_spec["name"], svc_spec["job_types"],
                                        job_type_key_to_id, type_dim_id, brand_dim_id, type_name_to_id, brand_name_to_id)
                except Exception as exc:
                    await db.rollback()
                    print(f"  ! FAILED: {svc_spec['name']}: {exc}")

        await db.commit()
        print("\nDone.")


if __name__ == "__main__":
    asyncio.run(run())

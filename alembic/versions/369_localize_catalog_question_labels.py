"""Localize every catalog question label to the Punjabi/English mix.

Replaces the earlier, never-deployed 369 that localized only the AC type
question. That one filtered on master_services.slug IN ('ac_repair',
'ac_installation', 'ac_maintenance', 'ac_gas_refill') -- slugs that come
from scripts/configure_ac_catalog.py and exist in no deployed database,
where the Air Conditioner service is the single slug 'air-conditioner'
with four job types. It therefore matched zero rows.

Matching on (question_key, current label) instead is both precise and
idempotent: a second run finds nothing because the English label is gone.
It also keeps question keys whose wording differs per job type
(furniture_type, item_type, mount_type, device_type, connection_type,
camera_count) on separate translations.

Revision ID: 369
Revises: 368
"""
import sqlalchemy as sa
from alembic import op


revision = "369"
down_revision = "368"
branch_labels = None
depends_on = None


# (question_key, English label, Punjabi/English label)
LABELS = [
    ("ac_type", "What type of AC is it?", "ਇਹ ਕਿਸ type ਦਾ ac ਹੈ?"),
    ("affected_points", "How many points are affected?", "ਕਿੰਨੇ points affected ਹਨ?"),
    ("area_type", "Interior or exterior?", "Interior ਜਾਂ exterior?"),
    ("brand", "Which AC brand is it?", "ਇਹ ਕਿਹੜਾ ac brand ਹੈ?"),
    ("brand", "Which brand?", "ਕਿਹੜਾ brand ਹੈ?"),
    ("brand", "Which brand is it?", "ਇਹ ਕਿਹੜਾ brand ਹੈ?"),
    ("build_type", "What kind of setup is this?", "ਇਹ ਕਿਸ ਤਰ੍ਹਾਂ ਦਾ setup ਹੈ?"),
    ("camera_count", "How many cameras are affected?", "ਕਿੰਨੇ cameras affected ਹਨ?"),
    ("camera_count", "How many cameras are needed?", "ਕਿੰਨੇ cameras ਚਾਹੀਦੇ ਹਨ?"),
    ("capacity", "What is the capacity (litres)?", "Capacity ਕਿੰਨੀ ਹੈ (litres)?"),
    ("chimney_type", "What type of chimney is it?", "ਇਹ ਕਿਸ type ਦੀ chimney ਹੈ?"),
    ("components", "Which components need installing/upgrading?", "ਕਿਹੜੇ components install/upgrade ਕਰਨੇ ਹਨ?"),
    ("connection_type", "How is it connected?", "ਇਹ ਕਿਵੇਂ connect ਕੀਤਾ ਹੋਇਆ ਹੈ?"),
    ("connection_type", "How should it connect?", "ਇਹ ਕਿਵੇਂ connect ਕਰਨਾ ਹੈ?"),
    ("coverage_area", "How large is the area to cover?", "ਕਿੰਨੇ ਵੱਡੇ area ਨੂੰ cover ਕਰਨਾ ਹੈ?"),
    ("data_backup", "Does existing data need to be backed up first?", "ਕੀ ਪਹਿਲਾਂ existing data ਦਾ backup ਲੈਣਾ ਹੈ?"),
    ("device_type", "What is being installed?", "ਕੀ install ਕੀਤਾ ਜਾ ਰਿਹਾ ਹੈ?"),
    ("device_type", "What needs repair?", "ਕਿਸ ਚੀਜ਼ ਦੀ repair ਕਰਨੀ ਹੈ?"),
    ("duct_or_ductless", "Ducted or ductless?", "Ducted ਜਾਂ ductless?"),
    ("filter_type", "What type of filter does it have?", "ਇਸ ਵਿੱਚ ਕਿਸ type ਦਾ filter ਹੈ?"),
    ("fixture_type", "What needs to be installed?", "ਕੀ install ਕਰਨਾ ਹੈ?"),
    ("fridge_type", "What type of refrigerator is it?", "ਇਹ ਕਿਸ type ਦਾ refrigerator ਹੈ?"),
    ("furniture_type", "What furniture needs repair?", "ਕਿਹੜੇ furniture ਦੀ repair ਕਰਨੀ ਹੈ?"),
    ("furniture_type", "What needs to be assembled/installed?", "ਕੀ assemble/install ਕਰਨਾ ਹੈ?"),
    ("geyser_type", "What type of geyser is it?", "ਇਹ ਕਿਸ type ਦਾ geyser ਹੈ?"),
    ("infestation_level", "How severe is the infestation?", "Infestation ਕਿੰਨੀ severe ਹੈ?"),
    ("installation_location", "Where will it be installed?", "ਇਹ ਕਿੱਥੇ install ਹੋਵੇਗਾ?"),
    ("isp_provided", "Is this the ISP's router or a new one?", "ਇਹ ISP ਦਾ router ਹੈ ਜਾਂ ਨਵਾਂ?"),
    ("issue_duration", "How long has this been happening?", "ਇਹ ਕਿੰਨੇ ਸਮੇਂ ਤੋਂ ਹੋ ਰਿਹਾ ਹੈ?"),
    ("issue_location", "Where is the issue?", "Issue ਕਿੱਥੇ ਹੈ?"),
    ("issue_scope", "Is the issue everywhere or in specific areas?", "ਕੀ issue ਹਰ ਥਾਂ ਹੈ ਜਾਂ ਕਿਸੇ ਖਾਸ area ਵਿੱਚ?"),
    ("item_type", "What needs repair?", "ਕਿਸ ਚੀਜ਼ ਦੀ repair ਕਰਨੀ ਹੈ?"),
    ("item_type", "What needs to be installed?", "ਕੀ install ਕਰਨਾ ਹੈ?"),
    ("laptop_brand", "What is the laptop brand?", "Laptop ਦਾ brand ਕਿਹੜਾ ਹੈ?"),
    ("last_filter_change", "When were filters last changed?", "Filters ਆਖਰੀ ਵਾਰ ਕਦੋਂ ਬਦਲੇ ਸਨ?"),
    ("last_service", "When was it last serviced?", "ਇਸ ਦੀ ਆਖਰੀ service ਕਦੋਂ ਹੋਈ ਸੀ?"),
    ("last_service", "When was the AC last serviced?", "Ac ਦੀ ਆਖਰੀ service ਕਦੋਂ ਹੋਈ ਸੀ?"),
    ("leak_duration", "How long has this been happening?", "ਇਹ ਕਿੰਨੇ ਸਮੇਂ ਤੋਂ ਹੋ ਰਿਹਾ ਹੈ?"),
    ("leak_location", "Where is the leakage?", "Leakage ਕਿੱਥੇ ਹੈ?"),
    ("location", "Indoor, outdoor, or both?", "Indoor, outdoor, ਜਾਂ ਦੋਵੇਂ?"),
    ("machine_type", "What type of washing machine is it?", "ਇਹ ਕਿਸ type ਦੀ washing machine ਹੈ?"),
    ("maintenance_goal", "What do you need from this service?", "ਤੁਹਾਨੂੰ ਇਸ service ਤੋਂ ਕੀ ਚਾਹੀਦਾ ਹੈ?"),
    ("material", "What is it made of?", "ਇਹ ਕਿਸ ਚੀਜ਼ ਦਾ ਬਣਿਆ ਹੋਇਆ ਹੈ?"),
    ("microwave_type", "What type of microwave is it?", "ਇਹ ਕਿਸ type ਦਾ microwave ਹੈ?"),
    ("mount_type", "How should it be installed?", "ਇਹ ਕਿਵੇਂ install ਕਰਨਾ ਹੈ?"),
    ("mount_type", "Where will it be placed?", "ਇਹ ਕਿੱਥੇ ਰੱਖਿਆ ਜਾਵੇਗਾ?"),
    ("paint_provided", "Will you provide the paint or should we?", "Paint ਤੁਸੀਂ ਦਿਓਗੇ ਜਾਂ ਅਸੀਂ?"),
    ("panel_age", "Roughly how old is the electrical panel?", "Electrical panel ਲਗਭਗ ਕਿੰਨਾ ਪੁਰਾਣਾ ਹੈ?"),
    ("pest_type", "What pest issue are you facing?", "ਤੁਹਾਨੂੰ ਕਿਹੜੀ pest ਦੀ ਸਮੱਸਿਆ ਹੈ?"),
    ("point_ready", "Is the electrical point already there?", "ਕੀ electrical point ਪਹਿਲਾਂ ਤੋਂ ਹੈ?"),
    ("points_needed", "How many new points are needed?", "ਕਿੰਨੇ ਨਵੇਂ points ਚਾਹੀਦੇ ਹਨ?"),
    ("power_point_ready", "Is a dedicated power point already available?", "ਕੀ dedicated power point ਪਹਿਲਾਂ ਤੋਂ available ਹੈ?"),
    ("property_size", "Approximate area (BHK / sq ft)?", "ਲਗਭਗ area ਕਿੰਨਾ ਹੈ (BHK / sq ft)?"),
    ("purifier_type", "What type of purifier is it?", "ਇਹ ਕਿਸ type ਦਾ purifier ਹੈ?"),
    ("reason", "Why is a new panel/MCB needed?", "ਨਵਾਂ panel/MCB ਕਿਉਂ ਚਾਹੀਦਾ ਹੈ?"),
    ("recording", "Local storage (DVR/NVR) or cloud recording?", "Local storage (DVR/NVR) ਜਾਂ cloud recording?"),
    ("room_count", "How many rooms / how much area (sq ft)?", "ਕਿੰਨੇ rooms / ਕਿੰਨਾ area (sq ft)?"),
    ("screen_size", "What is the screen size (inches)?", "Screen size ਕਿੰਨਾ ਹੈ (inches)?"),
    ("service_needed", "What do you need done?", "ਤੁਸੀਂ ਕੀ ਕਰਵਾਉਣਾ ਚਾਹੁੰਦੇ ਹੋ?"),
    ("symptom_when", "When does the issue happen?", "Issue ਕਦੋਂ ਆਉਂਦਾ ਹੈ?"),
    ("tank_capacity", "Approximate tank capacity (litres)?", "ਲਗਭਗ tank capacity (litres)?"),
    ("tv_type", "What type of TV is it?", "ਇਹ ਕਿਸ type ਦਾ tv ਹੈ?"),
    ("warranty_status", "Is it still under manufacturer warranty?", "ਕੀ ਇਹ ਹਾਲੇ ਵੀ manufacturer warranty ਵਿੱਚ ਹੈ?"),
    ("warranty_status", "Is it under manufacturer warranty?", "ਕੀ ਇਹ manufacturer warranty ਵਿੱਚ ਹੈ?"),
    ("water_source", "What is the water source?", "Water source ਕੀ ਹੈ?"),
    ("wifi_available", "Is WiFi available at the door?", "ਕੀ ਦਰਵਾਜ਼ੇ ਕੋਲ WiFi available ਹੈ?"),
]

_SQL = sa.text(
    "UPDATE catalog_questions SET label = :new_label, updated_at = now() "
    "WHERE question_key = :question_key AND label = :old_label"
)


def _relabel(pairs) -> None:
    conn = op.get_bind()
    total = 0
    for question_key, old_label, new_label in pairs:
        total += conn.execute(_SQL, {
            "question_key": question_key, "old_label": old_label, "new_label": new_label,
        }).rowcount
    print(f"[369] relabelled {total} catalog_questions rows")


def upgrade() -> None:
    _relabel(LABELS)


def downgrade() -> None:
    _relabel([(key, new, old) for key, old, new in LABELS])

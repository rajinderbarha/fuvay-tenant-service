"""Populate rebuilt Home Services categories skipped by the original seed.

Revision ID: 349
Revises: 348
"""
from alembic import op
import sqlalchemy as sa

revision = "349"
down_revision = "348"
branch_labels = None
depends_on = None


def upgrade():
    # Only empty catalogs: preserve all administrator edits and retirements.
    op.execute(sa.text("""
        INSERT INTO category_skills
            (category_id,code,name,description,status,requires_verification,display_order)
        SELECT c.id, s.code, s.name, s.description, 'active', s.verify, s.ordering
          FROM service_categories c
          CROSS JOIN (VALUES
            ('ac_diagnostics','AC Diagnostics','Diagnose cooling, electrical and airflow faults.',true,10),
            ('ac_repair','AC Repair','Repair approved AC components after diagnosis.',true,20),
            ('ac_installation','AC Installation','Install and commission supported AC systems.',true,30),
            ('ac_uninstallation','AC Uninstallation','Safely disconnect and remove AC systems.',true,40),
            ('ac_maintenance','AC Maintenance / Servicing','Perform preventive maintenance and routine servicing.',false,50),
            ('ac_gas_refill','AC Gas Refill','Inspect, recover and recharge refrigerant.',true,60),
            ('refrigerant_handling','Refrigerant Handling','Handle refrigerants using approved safety practices.',true,70),
            ('electrical_safety','Electrical Safety','Apply electrical isolation and safe-work procedures.',true,80)
          ) AS s(code,name,description,verify,ordering)
         WHERE c.vertical_type='home_services' AND c.is_active=true
           AND NOT EXISTS (SELECT 1 FROM category_skills cs WHERE cs.category_id=c.id)
        ON CONFLICT (category_id,code) DO NOTHING
    """))


def downgrade():
    # Data may already be assigned to technicians. Never delete those skills.
    pass

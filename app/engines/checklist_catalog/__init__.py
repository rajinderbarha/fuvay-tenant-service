"""Checklist Catalog Engine — canonical, job-type-mapped operational checklists.

Consolidates the previously disconnected checklist systems
(quote_checklist.SjChecklistTemplate*, field_ops.ServiceChecklistTemplate*,
admin_catalog.MasterChecklistItem) onto one reusable-template + published-
version + exact-Job-Type-mapping model, anchored on the existing canonical
MasterServiceJobType / ServiceJobWorkflow hierarchy. See models.py for the
full entity set and constants.py for the controlled vocabularies.
"""

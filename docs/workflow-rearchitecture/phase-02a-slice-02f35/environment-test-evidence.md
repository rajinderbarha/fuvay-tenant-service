# Environment Test Evidence

No environmental exclusions were required for this slice's targeted or
regression runs. `tests/test_phase2f35_critical_authorization_batch.py`
(34/34) and `tests/test_phase2f*.py` (full suite) both ran to completion
under the repo's standard local Python 3.12 / pytest-asyncio environment
with no skips attributable to missing services, network access, or
platform gating. The only warnings observed (FastAPI duplicate-operation-
ID warnings on `service_setup.templates_router`, and a handful of
pre-existing `pytest.mark.asyncio` warnings on synchronous test functions
in `test_phase2f4_tenant_portal_mutation_enforcement.py` /
`test_phase2f5b_finance_hub_platform_authorization.py` /
`test_phase2f5c_package_commerce_platform_authorization.py`) are
pre-existing, unrelated to this slice's modules, and did not affect pass/
fail outcomes.

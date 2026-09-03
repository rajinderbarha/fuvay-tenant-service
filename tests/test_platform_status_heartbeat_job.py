from pathlib import Path


def test_platform_status_heartbeat_is_live_and_started_by_lifespan():
    root = Path(__file__).resolve().parents[1]
    job = (root / "app/jobs/platform_status.py").read_text(encoding="utf-8")
    main = (root / "app/main.py").read_text(encoding="utf-8")

    assert "async def run_once" in job
    assert 'record_heartbeat(db, "core_services"' in job
    assert "get_redis().ping()" in job
    assert '("platform_status", platform_status_loop)' in main
    assert "for task in background_tasks" in main
    assert "task.cancel()" in main


def test_compliance_and_job_sla_tasks_have_distinct_registry_entries():
    main = (Path(__file__).resolve().parents[1] / "app/main.py").read_text(encoding="utf-8")
    assert '("compliance_sla", compliance_sla_loop)' in main
    assert '("sla_breach", sla_breach_loop)' in main

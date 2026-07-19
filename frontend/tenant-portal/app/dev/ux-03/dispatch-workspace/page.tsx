import { OperationalWorkspace } from "../../../../components/ux03/patterns/OperationalWorkspace";
import { FIXTURE_SERVICE_JOBS, FIXTURE_TEAM_MEMBERS } from "../../../../lib/ux03/fixtures";

export default function DispatchWorkspace() {
  const unassigned = FIXTURE_SERVICE_JOBS.filter((j) => !j.assignedTechnicianId);
  const technicians = FIXTURE_TEAM_MEMBERS.filter((m) => m.role === "technician");
  return (
    <OperationalWorkspace
      title="Assignment / Dispatch"
      description="Technician availability, workload, skills — no AI-matching claim (not confirmed as implemented in the repo)."
      queue={<div>{unassigned.map((j) => <p key={j.id}>{j.serviceName} — {j.customerName}</p>)}</div>}
      detail={<div>
        <p>Select a job from the queue to assign a technician.</p>
      </div>}
      sideContext={<div>
        <h4>Technicians</h4>
        {technicians.map((t) => (
          <p key={t.id}>{t.name} — {t.technicianDetail?.availability} · {t.technicianDetail?.skills.join(", ")}</p>
        ))}
      </div>}
    />
  );
}

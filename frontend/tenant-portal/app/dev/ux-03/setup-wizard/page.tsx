"use client";
import { PageShell } from "@serviceos/design-system";
import { SetupWizard, type WizardStep } from "../../../../components/ux03/patterns/SetupWizard";

const steps: WizardStep[] = [
  { id: "account", label: "Account Created", render: () => <p>Account created — auto-completed on signup.</p> },
  { id: "profile", label: "Business Profile", render: ({ goNext }) => <div><p>Legal name, display name, vertical.</p><button onClick={goNext}>Next</button></div> },
  { id: "registration", label: "Registration/Tax", render: ({ goNext, goBack }) => <div><p>Registration number, tax ID.</p><button onClick={goBack}>Back</button> <button onClick={goNext}>Next</button></div> },
  { id: "owner", label: "Owner Info", render: ({ goNext, goBack }) => <div><p>Owner name and contact.</p><button onClick={goBack}>Back</button> <button onClick={goNext}>Next</button></div> },
  { id: "address", label: "Address", render: ({ goNext, goBack }) => <div><p>Registered address.</p><button onClick={goBack}>Back</button> <button onClick={goNext}>Next</button></div> },
  { id: "categories", label: "Service Categories", render: ({ goNext, goBack }) => <div><p>AC Repair, Plumbing, Electrical.</p><button onClick={goBack}>Back</button> <button onClick={goNext}>Next</button></div> },
  { id: "areas", label: "Service Areas", render: ({ goNext, goBack }) => <div><p>Select coverage zones.</p><button onClick={goBack}>Back</button> <button onClick={goNext}>Next</button></div> },
  { id: "team", label: "Team Setup", optional: true, render: ({ goNext, goBack }) => <div><p>Invite staff/technicians (optional at this stage).</p><button onClick={goBack}>Back</button> <button onClick={goNext}>Next</button></div> },
  { id: "package", label: "Package/Deposit", render: ({ goNext, goBack }) => <div><p>Select package plan; security deposit requirement shown separately.</p><button onClick={goBack}>Back</button> <button onClick={goNext}>Next</button></div> },
  { id: "review", label: "Review Summary", render: ({ goBack }) => <div><p>Review all sections before submitting.</p><button onClick={goBack}>Back</button> <button>Submit for Review</button></div> },
];

export default function SetupWizardShowcase() {
  return (
    <PageShell>
      <SetupWizard
        title="Business Setup"
        description="Save/resume supported at every step; blocked/optional steps marked."
        steps={steps}
        onSaveDraft={(id) => console.log("draft saved (mock):", id)}
      />
    </PageShell>
  );
}

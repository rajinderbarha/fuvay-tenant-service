import { LegalDocument } from "../../components/legal/LegalDocument";

export default function SecurityPage() {
  return <LegalDocument title="Security at ServiceOS" updated="11 August 2026"
    intro="ServiceOS uses layered controls to protect accounts, business data, and customer operations."
    sections={[
      { heading: "Account security", paragraphs: ["Passwords are stored using one-way hashing. Contact verification, session controls, audit logging, and role-based permissions protect workspace access."] },
      { heading: "Data protection", paragraphs: ["Data is protected in transit, access is tenant-scoped, and sensitive mutations are authorized server-side."] },
      { heading: "File safety", paragraphs: ["Uploads are restricted by context, size, extension, MIME type, and verified file signatures before storage."] },
      { heading: "Report a concern", paragraphs: ["Report suspected vulnerabilities or unauthorized activity promptly to ServiceOS support. Do not include sensitive customer data in the initial report."] },
    ]}/>;
}

import { LegalDocument } from "../../components/legal/LegalDocument";

export default function TermsPage() {
  return <LegalDocument title="Terms of Service" updated="11 August 2026"
    intro="These terms govern use of the ServiceOS business workspace and related services."
    sections={[
      { heading: "Your account", paragraphs: ["You must provide accurate information, keep login credentials secure, and be authorized to act for the business you register."] },
      { heading: "Business setup and review", paragraphs: ["Creating an account creates a draft workspace. Business information is submitted for administrative review only after you complete setup and explicitly submit it."] },
      { heading: "Acceptable use", paragraphs: ["You may not misuse the service, interfere with its operation, upload unlawful or malicious material, or access data belonging to another user or business."] },
      { heading: "Payments and activation", paragraphs: ["No package or payment is required during signup. Applicable deposits, credits, commissions, or package terms are disclosed before activation or purchase."] },
      { heading: "Suspension and termination", paragraphs: ["ServiceOS may restrict access when required for security, legal compliance, fraud prevention, or a material breach of these terms."] },
    ]}/>;
}

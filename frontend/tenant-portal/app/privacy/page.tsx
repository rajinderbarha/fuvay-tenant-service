import { LegalDocument } from "../../components/legal/LegalDocument";

export default function PrivacyPage() {
  return <LegalDocument title="Privacy Notice" updated="11 August 2026"
    intro="This notice explains how ServiceOS handles information provided during signup and business operations."
    sections={[
      { heading: "Information we collect", paragraphs: ["We collect owner contact details, verification data, business identity information, documents, service configuration, and operational records needed to provide the workspace."] },
      { heading: "How we use information", paragraphs: ["We use information to create and secure accounts, verify businesses, operate requested services, prevent fraud, provide support, and meet legal obligations."] },
      { heading: "Consent", paragraphs: ["Required authorization and terms consent are recorded when you create the workspace. Optional marketing consent is recorded separately and can be withdrawn."] },
      { heading: "Sharing and retention", paragraphs: ["Information is shared only with authorized processors, service providers, or authorities where necessary. Records are retained according to security, operational, and legal requirements."] },
      { heading: "Your choices", paragraphs: ["You may request access, correction, or other applicable privacy rights through ServiceOS support. Some records must be retained for legal or security reasons."] },
    ]}/>;
}

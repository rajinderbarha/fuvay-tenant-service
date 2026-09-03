import type { Metadata } from "next";
import Link from "next/link";
import { services } from "../../lib/site";
export const metadata: Metadata = { title: "Home Services in Punjab", description: "Explore Fuvay home services published by approved local providers across Punjab." };
export default function ServicesPage(){return <><section className="page-hero shell"><span className="kicker">Service directory</span><h1>Home services available through local providers.</h1><p>Fuvay only shows a service after an eligible provider has published it for your PIN code. Availability and pricing are checked during booking.</p></section><section className="section shell"><div className="service-grid">{services.map(s=><Link className="service-card" href={`/services/${s.slug}/`} key={s.slug}><div className="service-image"><img src={s.image} alt=""/></div><div><h3>{s.name}</h3><p className="punjabi">{s.punjabi}</p><p>{s.description}</p><span>View service →</span></div></Link>)}</div></section></>}

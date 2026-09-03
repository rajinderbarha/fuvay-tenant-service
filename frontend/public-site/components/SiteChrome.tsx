import Link from "next/link";
import { ArrowUpRight, Instagram, Menu, MessageCircle } from "lucide-react";
import { links } from "../lib/site";

export function Header() {
  return <header className="header"><div className="shell nav">
    <Link className="brand" href="/"><img src="/brand/fuvay-logo.png" alt="Fuvay" /><span>Fuvay</span></Link>
    <nav aria-label="Main navigation">
      <Link href="/services/">Services</Link><Link href="/cities/ludhiana/">Cities</Link><Link href="/warranty-safety/">Warranty & safety</Link><Link href="/providers/">For providers</Link><Link href="/about/">About</Link>
    </nav>
    <a className="button small" href={links.whatsapp}>Book a service <ArrowUpRight size={16}/></a>
    <button className="menu" aria-label="Open menu"><Menu /></button>
  </div></header>;
}

export function BookingChoices({ compact = false }: { compact?: boolean }) {
  return <div className={compact ? "booking-links compact" : "booking-links"} id="booking-options">
    <a className="button" href={links.whatsapp}><MessageCircle size={18}/> Book on WhatsApp</a>
    <a className="button secondary" href={links.instagram}><Instagram size={18}/> Instagram</a>
    <a className="text-link" href={links.app}>Use customer app <ArrowUpRight size={15}/></a>
  </div>;
}

export function Footer() {
  return <footer><div className="shell footer-grid"><div><Link className="brand" href="/"><img src="/brand/fuvay-logo.png" alt=""/><span>Fuvay</span></Link><p>Local home-service booking built around PIN-code coverage, provider accountability and customer evidence.</p></div><div><h3>Customers</h3><Link href="/services/">Services</Link><Link href="/warranty-safety/">Warranty & safety</Link><Link href="/contact/">Help & contact</Link></div><div><h3>Providers</h3><a href={links.provider}>Login / sign up</a><Link href="/providers/">How it works</Link></div><div><h3>Company</h3><Link href="/about/">About</Link><Link href="/legal/">Terms & privacy</Link></div></div><div className="shell footer-bottom">© {new Date().getFullYear()} Fuvay · Made for Punjab</div></footer>;
}

"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Grid, Calendar, User, Plus } from "lucide-react";

export default function BottomNav() {
  const pathname = usePathname();
  const isActive = (p: string) => pathname === p || pathname?.startsWith(p + "/");

  return (
    <nav className="co-bottom-nav">
      <Link href="/customer/home-services" className={`co-nav-item ${isActive("/customer/home-services") && pathname === "/customer/home-services" ? "active" : ""}`}>
        <Home size={20} /><span>Home</span>
      </Link>
      <Link href="/customer/home-services" className={`co-nav-item ${pathname === "/customer/home-services" ? "active" : ""}`}>
        <Grid size={20} /><span>Services</span>
      </Link>
      <Link href="/customer/home-services/book" aria-label="Book Now">
        <div className="co-nav-fab"><Plus size={26} /></div>
      </Link>
      <Link href="/customer/bookings" className={`co-nav-item ${isActive("/customer/bookings") ? "active" : ""}`}>
        <Calendar size={20} /><span>Bookings</span>
      </Link>
      <Link href="/customer/profile" className={`co-nav-item ${isActive("/customer/profile") ? "active" : ""}`}>
        <User size={20} /><span>Profile</span>
      </Link>
    </nav>
  );
}

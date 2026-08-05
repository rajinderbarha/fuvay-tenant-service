"use client";
/**
 * TRACK-TECHNICIAN — Track technician.
 *
 * Renders ONLY backend-authoritative data from GET .../tracking-location:
 * real technician GPS (submitted by the technician's own device), real
 * timestamp/staleness, real customer-safe technician identity. There is no
 * ETA anywhere in this backend (no routing/distance service exists), so
 * none is shown or computed here. There is no mapping-tile provider
 * configured in this app, so the map is a schematic (grid + coral route)
 * plotting the real coordinates proportionally — not a real street map —
 * to avoid implying tile-accurate cartography that doesn't exist.
 */
import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import ErrorBanner from "../../../../../components/ErrorBanner";
import {
  getCustomerBookingDetail, getTrackingLocation, TrackingLocation,
} from "../../../../../lib/api/customer-home-services";

const POLL_MS = 15000;

const STATUS_LABEL: Record<string, string> = {
  accepted: "Technician assigned",
  scheduled: "Visit scheduled",
  on_the_way: "On the way",
};

const NOT_AVAILABLE_COPY: Record<string, string> = {
  not_yet_assigned: "A technician hasn't been assigned to this booking yet.",
  tracking_ended: "Tracking isn't available for this booking anymore.",
  location_unavailable: "Your technician hasn't shared a location yet. Try refreshing in a moment.",
};

function relativeTime(iso?: string): string {
  if (!iso) return "";
  const ms = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(ms / 60000);
  if (mins < 1) return "just now";
  if (mins === 1) return "1 min ago";
  return `${mins} min ago`;
}

/** Schematic (not geographic-accurate) projection of two real lat/lng points
 *  into a small SVG box, so the route/markers reflect real relative
 *  position without claiming real street-map cartography. */
function project(techLat: number, techLng: number, destLat?: number | null, destLng?: number | null) {
  const pad = 40, size = 300;
  if (destLat == null || destLng == null) {
    return { tech: { x: size / 2, y: size / 2 }, dest: null };
  }
  const minLat = Math.min(techLat, destLat), maxLat = Math.max(techLat, destLat);
  const minLng = Math.min(techLng, destLng), maxLng = Math.max(techLng, destLng);
  const spanLat = Math.max(maxLat - minLat, 0.0005);
  const spanLng = Math.max(maxLng - minLng, 0.0005);
  const toXY = (lat: number, lng: number) => ({
    x: pad + ((lng - minLng) / spanLng) * (size - 2 * pad),
    y: size - pad - ((lat - minLat) / spanLat) * (size - 2 * pad),
  });
  return { tech: toXY(techLat, techLng), dest: toXY(destLat, destLng) };
}

export default function TrackTechnicianPage() {
  const params = useParams();
  const router = useRouter();
  const bookingId = params.bookingId as string;

  const [detail, setDetail] = useState<any>(null);
  const [loc, setLoc] = useState<TrackingLocation | null>(null);
  const [error, setError] = useState<unknown>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadLocation = useCallback(() => {
    getTrackingLocation(bookingId).then(setLoc).catch(setError);
  }, [bookingId]);

  useEffect(() => {
    getCustomerBookingDetail(bookingId).then(setDetail).catch(setError);
    loadLocation();
  }, [bookingId, loadLocation]);

  // Poll only while the tab is visible and tracking is genuinely active —
  // bounded interval, no aggressive/backgrounded polling.
  useEffect(() => {
    function tick() {
      if (document.visibilityState === "visible" && loc?.available) loadLocation();
    }
    pollRef.current = setInterval(tick, POLL_MS);
    document.addEventListener("visibilitychange", tick);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [loadLocation, loc?.available]);

  const geo = loc?.available && loc.latitude != null && loc.longitude != null
    ? project(loc.latitude, loc.longitude, loc.destination_latitude, loc.destination_longitude)
    : null;

  return (
    <div className="co-container">
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "12px 0" }}>
        <button aria-label="Back" className="co-btn-secondary" style={{ minWidth: 44, minHeight: 44, padding: 0 }}
          onClick={() => router.back()}>‹</button>
        <div>
          <div style={{ fontSize: 18, fontWeight: 700 }}>Track technician</div>
          {detail && <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>{detail.booking_number}</div>}
        </div>
      </div>

      <ErrorBanner error={error} />

      {!loc ? (
        !error && <div className="co-skeleton" style={{ height: 300, marginBottom: 16 }} />
      ) : !loc.available ? (
        <div className="co-card" role="status" style={{ textAlign: "center", padding: 24 }}>
          {NOT_AVAILABLE_COPY[loc.reason ?? ""] ?? "Tracking isn't available right now."}
        </div>
      ) : (
        <>
          {geo && (
            <div className="co-card" style={{ marginBottom: 16, padding: 0, overflow: "hidden" }}
              role="img" aria-label={`Schematic map showing the technician's approximate position${geo.dest ? " and the route to your address" : ""}.`}>
              <svg viewBox="0 0 300 300" width="100%" height="260" aria-hidden="true">
                <defs>
                  <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
                    <path d="M 30 0 L 0 0 0 30" fill="none" stroke="var(--border)" strokeWidth="1" />
                  </pattern>
                </defs>
                <rect width="300" height="300" fill="var(--surface)" />
                <rect width="300" height="300" fill="url(#grid)" />
                {geo.dest && (
                  <path d={`M ${geo.tech.x} ${geo.tech.y} L ${geo.dest.x} ${geo.dest.y}`}
                    stroke="var(--danger)" strokeWidth="3" fill="none" strokeLinecap="round" />
                )}
                {geo.dest && (
                  <g transform={`translate(${geo.dest.x},${geo.dest.y})`}>
                    <circle r="9" fill="var(--surface)" stroke="var(--text-primary)" strokeWidth="2" />
                    <circle r="3" fill="var(--text-primary)" />
                  </g>
                )}
                <g transform={`translate(${geo.tech.x},${geo.tech.y})`}>
                  <circle r="13" fill="var(--danger)" stroke="var(--surface)" strokeWidth="3" />
                  <circle r="4" fill="#fff" />
                </g>
              </svg>
            </div>
          )}

          <div className="co-card" style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "var(--danger)", letterSpacing: 1, marginBottom: 4 }}>
              {(loc.job_status ?? "").toUpperCase().replace(/_/g, " ")}
            </div>
            <div style={{ fontSize: 22, fontWeight: 800, marginBottom: 4 }}>
              {STATUS_LABEL[loc.job_status ?? ""] ?? "Tracking active"}
            </div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
              Location updated {relativeTime(loc.recorded_at)}
              {loc.is_stale ? " · may be outdated" : ""}
            </div>
          </div>

          {loc.technician && (
            <div className="co-card" style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ width: 44, height: 44, borderRadius: "50%", background: "var(--border)",
                display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }} aria-hidden="true">👤</div>
              <div>
                <div style={{ fontWeight: 700 }}>{loc.technician.name}</div>
                <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>{loc.technician.role}</div>
              </div>
            </div>
          )}

          {detail?.address && (
            <div className="co-card" style={{ marginBottom: 16, display: "flex", gap: 10, alignItems: "center" }}>
              <span aria-hidden="true">📍</span>
              <span>{detail.address.address_line1}{detail.city ? `, ${detail.city}` : ""}</span>
            </div>
          )}

          <Link href={`/customer/chat?record_type=service_booking&record_id=${bookingId}`}
            className="co-btn-primary" style={{ background: "var(--danger)", boxShadow: "none",
              textAlign: "center", display: "block", marginBottom: 10 }}>
            Contact technician
          </Link>
          <div style={{ textAlign: "center" }}>
            <Link href={`/customer/complaints?record_type=service_booking&record_id=${bookingId}`}
              style={{ color: "var(--danger)", fontWeight: 600, textDecoration: "underline" }}>
              Report an issue
            </Link>
          </div>
        </>
      )}
    </div>
  );
}

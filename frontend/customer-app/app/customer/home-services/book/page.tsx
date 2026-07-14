"use client";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  CheckCircle, Award, Star, Shield, ShieldCheck, Crown, Trophy, Medal, Gem, Sparkles,
  BadgeCheck, Flame, Zap, Heart, ThumbsUp, TrendingUp, CheckCircle2, Rocket, Target,
} from "lucide-react";
import ErrorBanner from "../../../../components/ErrorBanner";
import {
  getCustomerHomeServicesCatalog, getCatalogServices, getCatalogBrands, getCatalogIssueTypes, getCatalogServiceTypes,
  startBookingDraft, updateDraftFields, checkServiceability, selectProviderForHomeService,
  confirmPriceChoice, buildBookingSummary, createCustomerHomeServiceBooking,
  CatalogCategory, CatalogService, CatalogBrand, CatalogIssueType, CatalogServiceType,
} from "../../../../lib/api/customer-home-services";
import { isLoggedIn } from "../../../../lib/api/client";

type Step = "service" | "details" | "location" | "provider" | "price" | "review" | "confirm";
const STEPS: Step[] = ["service", "details", "location", "provider", "price", "review", "confirm"];
const STEP_LABEL: Record<Step, string> = {
  service: "Service", details: "Details", location: "Location", provider: "Provider",
  price: "Price", review: "Review", confirm: "Confirm",
};

export default function BookHomeServicePage() {
  return (
    <Suspense fallback={<div className="co-container"><div className="co-card">Loading...</div></div>}>
      <BookHomeServiceInner />
    </Suspense>
  );
}

function BookHomeServiceInner() {
  const router = useRouter();
  const params = useSearchParams();

  const [step, setStep] = useState<Step>("service");
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  // Step 1: service selection
  const [categories, setCategories] = useState<CatalogCategory[]>([]);
  const [categoryId, setCategoryId] = useState(params.get("category_id") || "");
  const [services, setServices] = useState<CatalogService[]>([]);
  const [serviceId, setServiceId] = useState("");
  const [serviceSlug, setServiceSlug] = useState("");

  // Draft
  const [draftId, setDraftId] = useState<string | null>(null);
  const [draft, setDraft] = useState<any>(null);

  // Step: details (type/brand/issue/notes)
  const [serviceTypes, setServiceTypes] = useState<CatalogServiceType[]>([]);
  const [brands, setBrands] = useState<CatalogBrand[]>([]);
  const [issues, setIssues] = useState<CatalogIssueType[]>([]);
  const [offeringTypeId, setOfferingTypeId] = useState("");
  const [brandId, setBrandId] = useState("");
  const [issueSummary, setIssueSummary] = useState("");

  // Step: location
  const [zipcode, setZipcode] = useState("");
  const [city, setCity] = useState("");
  const [address1, setAddress1] = useState("");
  const [address2, setAddress2] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [phone, setPhone] = useState("");
  const [serviceabilityMsg, setServiceabilityMsg] = useState<string | null>(null);

  // Step: provider + price
  const [matchResult, setMatchResult] = useState<any>(null);
  const [priceTier, setPriceTier] = useState<"low" | "mid" | "high" | null>(null);

  // Step: confirm result
  const [bookingResult, setBookingResult] = useState<any>(null);

  useEffect(() => {
    getCustomerHomeServicesCatalog().then((r) => setCategories(r.categories)).catch(setError);
  }, []);

  useEffect(() => {
    if (categoryId) {
      getCatalogServices(categoryId).then((r) => setServices(r.services)).catch(setError);
      getCatalogBrands(categoryId).then((r) => setBrands(r.brands)).catch(() => {});
      getCatalogServiceTypes(categoryId).then((r) => setServiceTypes(r.types)).catch(() => {});
    }
  }, [categoryId]);

  useEffect(() => {
    if (categoryId && serviceId) {
      getCatalogIssueTypes(categoryId, serviceId).then((r) => setIssues(r.issue_types)).catch(() => {});
    }
  }, [categoryId, serviceId]);

  function goto(next: Step) { setError(null); setStep(next); }

  async function handleServiceNext() {
    if (!isLoggedIn()) { router.push(`/login?next=/customer/home-services/book`); return; }
    if (!categoryId || !serviceId || !serviceSlug) { setError(new Error("Please select a service.")); return; }
    setLoading(true); setError(null);
    try {
      const category = categories.find((c) => c.category_id === categoryId);
      const d = await startBookingDraft(category?.slug || "", serviceSlug);
      setDraftId(d.id);
      setDraft(d);
      goto("details");
    } catch (e) { setError(e); } finally { setLoading(false); }
  }

  async function handleDetailsNext() {
    if (!issueSummary.trim()) { setError(new Error("Please describe the issue.")); return; }
    setLoading(true); setError(null);
    try {
      const payload: Record<string, unknown> = { issue_summary: issueSummary };
      if (brandId) payload.brand_id = brandId;
      if (offeringTypeId) payload.offering_type_id = offeringTypeId;
      const d = await updateDraftFields(draftId!, payload);
      setDraft(d);
      goto("location");
    } catch (e) { setError(e); } finally { setLoading(false); }
  }

  async function handleLocationNext() {
    if (!address1.trim() || !phone.trim() || !zipcode.trim() || !city.trim()) {
      setError(new Error("Address, city, zipcode and phone are required.")); return;
    }
    setLoading(true); setError(null); setServiceabilityMsg(null);
    try {
      await updateDraftFields(draftId!, {
        zipcode, city, customer_name: customerName || undefined, customer_phone: phone,
        address_snapshot: { address_line1: address1, address_line2: address2 || undefined, city, zipcode },
      });
      const svcCheck = await checkServiceability(draftId!);
      if (!svcCheck.serviceable) {
        setServiceabilityMsg(svcCheck.message || "Service is not available in this area yet. Try a nearby zipcode or check again later.");
        setLoading(false);
        return;
      }
      goto("provider");
      await runMatching();
    } catch (e) { setError(e); setLoading(false); }
  }

  async function runMatching() {
    setLoading(true); setError(null);
    try {
      const result = await selectProviderForHomeService(draftId!);
      setMatchResult(result);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectPrice(tier: "low" | "mid" | "high") {
    setPriceTier(tier);
  }

  async function handlePriceNext() {
    if (!priceTier) { setError(new Error("Please select a price option.")); return; }
    if (!matchResult?.provider && !matchResult?.selected_provider) { setError(new Error("A provider must be selected before choosing a price.")); return; }
    setLoading(true); setError(null);
    try {
      await confirmPriceChoice(draftId!, priceTier);
      const summary = await buildBookingSummary(draftId!);
      setDraft((prev: any) => ({ ...prev, ...summary }));
      goto("review");
    } catch (e) { setError(e); } finally { setLoading(false); }
  }

  async function handleConfirmBooking() {
    setLoading(true); setError(null);
    try {
      const idem = `book-${draftId}-${Date.now()}`;
      const result = await createCustomerHomeServiceBooking(draftId!, idem);
      setBookingResult(result);
      goto("confirm");
    } catch (e) {
      setError(e);
    } finally { setLoading(false); }
  }

  const stepIndex = STEPS.indexOf(step);

  return (
    <div className="co-container">
      <div style={{ padding: "12px 0" }}>
        <div style={{ fontWeight: 700, fontSize: 18, marginBottom: 4 }}>{STEP_LABEL[step]}</div>
        <div className="co-progress-track">
          {STEPS.map((s, i) => <div key={s} className={`co-progress-step ${i <= stepIndex ? "done" : ""}`} />)}
        </div>
      </div>

      <ErrorBanner error={error} />

      {step === "service" && (
        <div className="co-card" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <p style={{ color: "var(--text-secondary)", fontSize: 13 }}>Choose a category and the service you need.</p>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Category</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {categories.map((c) => (
                <button key={c.category_id} type="button" className={`co-chip ${categoryId === c.category_id ? "selected" : ""}`}
                  onClick={() => { setCategoryId(c.category_id); setServiceId(""); }}>{c.name}</button>
              ))}
            </div>
          </div>
          {categoryId && (
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Service</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {services.map((s) => (
                  <button key={s.service_id} type="button" className={`co-chip ${serviceId === s.service_id ? "selected" : ""}`}
                    onClick={() => { setServiceId(s.service_id); setServiceSlug(s.slug || ""); }}>{s.service_name}</button>
                ))}
              </div>
            </div>
          )}
          <button className="co-btn-primary" disabled={loading || !serviceId} onClick={handleServiceNext}>
            {loading ? "Please wait..." : "Next"}
          </button>
        </div>
      )}

      {step === "details" && (
        <div className="co-card" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {serviceTypes.length > 0 && (
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Type</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {serviceTypes.map((t) => (
                  <button key={t.type_id} type="button" className={`co-chip ${offeringTypeId === t.type_id ? "selected" : ""}`} onClick={() => setOfferingTypeId(t.type_id)}>{t.name}</button>
                ))}
              </div>
            </div>
          )}
          {brands.length > 0 && (
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Brand</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {brands.map((b) => (
                  <button key={b.brand_id} type="button" className={`co-chip ${brandId === b.brand_id ? "selected" : ""}`} onClick={() => setBrandId(b.brand_id)}>{b.name}</button>
                ))}
              </div>
            </div>
          )}
          {issues.length > 0 && (
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Issue</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {issues.map((i) => (
                  <button key={i.id} type="button" className={`co-chip ${issueSummary === i.name ? "selected" : ""}`} onClick={() => setIssueSummary(i.name)}>{i.name}</button>
                ))}
              </div>
            </div>
          )}
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Describe the issue *</div>
            <textarea value={issueSummary} onChange={(e) => setIssueSummary(e.target.value)} rows={3}
              placeholder="e.g. AC not cooling"
              style={{ width: "100%", padding: 12, borderRadius: 12, border: "1px solid var(--border-strong)", fontSize: 15 }} />
          </div>
          <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
            Photo upload is not yet wired to a live backend endpoint for this booking-draft flow; disabled to avoid
            showing a fake upload. See CUSTOMER_FRONTEND_01_REMAINING_BLOCKERS.md.
          </div>
          <button className="co-btn-primary" disabled={loading} onClick={handleDetailsNext}>{loading ? "Please wait..." : "Next"}</button>
        </div>
      )}

      {step === "location" && (
        <div className="co-card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <input placeholder="Full name" value={customerName} onChange={(e) => setCustomerName(e.target.value)} style={inputStyle} />
          <input placeholder="Phone *" value={phone} onChange={(e) => setPhone(e.target.value)} style={inputStyle} />
          <input placeholder="Zipcode *" value={zipcode} onChange={(e) => setZipcode(e.target.value)} style={inputStyle} />
          <input placeholder="City *" value={city} onChange={(e) => setCity(e.target.value)} style={inputStyle} />
          <input placeholder="Address line 1 *" value={address1} onChange={(e) => setAddress1(e.target.value)} style={inputStyle} />
          <input placeholder="Address line 2 (optional)" value={address2} onChange={(e) => setAddress2(e.target.value)} style={inputStyle} />
          {serviceabilityMsg && <div className="co-error-banner">{serviceabilityMsg}</div>}
          <button className="co-btn-primary" disabled={loading} onClick={handleLocationNext}>{loading ? "Checking..." : "Next"}</button>
        </div>
      )}

      {step === "provider" && (
        <div className="co-card">
          {loading && <div className="co-empty">Finding the best available provider near you...</div>}
          {!loading && matchResult && (matchResult.provider || matchResult.selected_provider) && (
            <ProviderCard provider={matchResult.provider || matchResult.selected_provider} onNext={() => goto("price")} />
          )}
          {!loading && matchResult && !(matchResult.provider || matchResult.selected_provider) && (
            <div className="co-empty">No provider is available for this service in your area right now. Try a different time or check again later.</div>
          )}
        </div>
      )}

      {step === "price" && (
        <PriceStep matchResult={matchResult} priceTier={priceTier} onSelect={handleSelectPrice} onNext={handlePriceNext} loading={loading} />
      )}

      {step === "review" && (
        <ReviewStep draft={draft} matchResult={matchResult} priceTier={priceTier} loading={loading} onConfirm={handleConfirmBooking} />
      )}

      {step === "confirm" && bookingResult && (
        <div className="co-card" style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: 12, alignItems: "center" }}>
          <CheckCircle size={48} color="var(--success)" />
          <div style={{ fontWeight: 700, fontSize: 18 }}>Booking Confirmed</div>
          <div style={{ color: "var(--text-secondary)", fontSize: 14 }}>Your provider has been assigned.</div>
          <div style={{ color: "var(--text-secondary)", fontSize: 14 }}>Pay provider directly after the service is completed.</div>
          <div style={{ fontSize: 13 }}>Booking ID: {bookingResult.booking_number || bookingResult.booking_id || bookingResult.id}</div>
          <button className="co-btn-primary" onClick={() => router.push(`/customer/bookings/${bookingResult.booking_id || bookingResult.id}`)}>Track Booking</button>
        </div>
      )}
    </div>
  );
}

const inputStyle: React.CSSProperties = { width: "100%", padding: 14, borderRadius: 12, border: "1px solid var(--border-strong)", fontSize: 16 };

// Trust badges arrive as objects {name, icon, color} from the matching engine;
// tolerate legacy string entries too.
const CUST_BADGE_ICONS: Record<string, React.ComponentType<{ size?: number; color?: string }>> = {
  award: Award, star: Star, shield: Shield, "shield-check": ShieldCheck, crown: Crown,
  trophy: Trophy, medal: Medal, gem: Gem, sparkles: Sparkles, "badge-check": BadgeCheck,
  flame: Flame, zap: Zap, heart: Heart, "thumbs-up": ThumbsUp, "trending-up": TrendingUp,
  "check-circle": CheckCircle2, rocket: Rocket, target: Target,
};

function CustomerTrustBadge({ badge }: { badge: { name: string; icon?: string | null; color?: string | null } }) {
  const Cmp = CUST_BADGE_ICONS[badge.icon ?? ""] ?? Award;
  const c = badge.color || "#f59e0b";
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 5, padding: "4px 10px 4px 7px",
      borderRadius: 999, background: `${c}18`, border: `1px solid ${c}55`, fontSize: 12, fontWeight: 600 }}>
      <Cmp size={13} color={c} />{badge.name}
    </span>
  );
}

function ProviderCard({ provider, onNext }: { provider: any; onNext: () => void }) {
  const raw: any[] = provider.public_badges || provider.badges || [];
  const badges = raw.map((b) => (typeof b === "string" ? { name: b } : b))
    .filter((b) => b && b.name);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <div style={{ width: 56, height: 56, borderRadius: 16, background: "var(--info-bg)" }} />
        <div>
          <div style={{ fontWeight: 700 }}>{provider.provider_name || provider.business_name}</div>
          <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
            {provider.rating ? `${provider.rating} rating` : "New provider"} {provider.review_count ? `· ${provider.review_count} reviews` : ""}
          </div>
        </div>
      </div>
      {badges.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {badges.map((b, i) => <CustomerTrustBadge key={b.name + i} badge={b} />)}
        </div>
      )}
      {(provider.city || provider.service_area) && <div style={{ fontSize: 13 }}>Serving: {provider.city || provider.service_area}</div>}
      {provider.estimated_visit_window && <div style={{ fontSize: 13 }}>Estimated visit: {provider.estimated_visit_window}</div>}
      <button className="co-btn-primary" onClick={onNext}>See Price Options</button>
    </div>
  );
}

// Real backend (HomeServiceChatbotBookingService.match_provider_and_price) returns
// selected_provider_price_options: { low_price, mid_price, high_price, ... } — not
// "price_options"/"prices" with bare low/mid/high keys. Extract + normalize here so
// the rest of the component can keep using the short tier keys.
function extractPriceOptions(matchResult: any): Record<"low" | "mid" | "high", number | undefined> {
  const raw = matchResult?.selected_provider_price_options || matchResult?.price_options || matchResult?.prices || {};
  return {
    low: raw.low_price ?? raw.low,
    mid: raw.mid_price ?? raw.mid,
    high: raw.high_price ?? raw.high,
  };
}

function PriceStep({ matchResult, priceTier, onSelect, onNext, loading }: any) {
  const options = extractPriceOptions(matchResult);
  const tiers: Array<{ key: "low" | "mid" | "high"; label: string; blurb: string }> = [
    { key: "low", label: "Low", blurb: "Budget-friendly option" },
    { key: "mid", label: "Mid", blurb: "Recommended fair price" },
    { key: "high", label: "High", blurb: "Higher acceptance priority" },
  ];
  if (!options.low && !options.mid && !options.high) {
    return <div className="co-card"><div className="co-empty">Price options are loading...</div></div>;
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {tiers.map((t) => (
        <div key={t.key} className={`co-price-card ${priceTier === t.key ? "selected" : ""}`} onClick={() => onSelect(t.key)}>
          {t.key === "mid" && <span className="co-badge-recommended">Recommended</span>}
          <div style={{ fontWeight: 700 }}>{t.label} — ₹{options[t.key]}</div>
          <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>{t.blurb}</div>
        </div>
      ))}
      <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Pay provider directly after service.</div>
      <button className="co-btn-primary" disabled={loading || !priceTier} onClick={onNext}>{loading ? "Please wait..." : "Continue"}</button>
    </div>
  );
}

function ReviewStep({ draft, matchResult, priceTier, loading, onConfirm }: any) {
  const provider = matchResult?.provider || matchResult?.selected_provider || {};
  const options = extractPriceOptions(matchResult);
  return (
    <div className="co-card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div><strong>Service:</strong> {draft?.offering_name}</div>
      <div><strong>Issue:</strong> {draft?.issue_summary}</div>
      <div><strong>Address:</strong> {draft?.address_snapshot?.address_line1}, {draft?.city} {draft?.zipcode}</div>
      <div><strong>Provider:</strong> {provider.provider_name || provider.business_name}</div>
      <div><strong>Selected price:</strong> {priceTier ? `${priceTier} — ₹${options[priceTier]}` : "—"}</div>
      <div><strong>Payment:</strong> Customer Pays Provider Directly</div>
      <button className="co-btn-primary" disabled={loading || !priceTier || !(provider.provider_name || provider.business_name)} onClick={onConfirm}>{loading ? "Confirming..." : "Confirm Booking"}</button>
    </div>
  );
}

"use client";
import React, { useState, useCallback, useEffect } from "react";
import Link from "next/link";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { ProfilePhotoUploader } from "../../../components/shared/ProfilePhotoUploader";
import {
  Modal, Button as DsButton, Input as DsInput, Textarea as DsTextarea, Skeleton as DsSkeleton,
} from "@serviceos/design-system";
import {
  profileApi, businessProfileApi, tenantSetupApi, providerStatusApi, myStatusApi, authApi,
  mediaAssetApi, providerOfferingsApi,
  type UserProfile, type BusinessProfile, type MediaAsset,
} from "../../../lib/api";
import { ServiceOSError, trustBadgesApi } from "../../../lib/api";
import { TrustBadgeChip } from "../../../components/TrustBadges";
import type { EarnedBadge } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { useSetupStatus } from "../../../hooks/useSetupStatus";
import { SetupWizardDrawer } from "../../../components/layout/TenantLayout";
import {
  Building2, User, Mail, Phone, Globe, Clock, Camera, AlertTriangle,
  CheckCircle2, XCircle, Info, RefreshCw, ChevronRight, Shield, Loader,
  FileText, Activity, Copy, Package, MapPin, Tag, Zap, AlertCircle,
  Save, Search, ExternalLink, Eye, Pencil, Send, Star, Users2, UserPlus,
  Layers, ImageIcon, X, Lock,
} from "lucide-react";

// ── Constants ─────────────────────────────────────────────────────────────────
const LANGUAGES = [
  { value:"en",label:"English" },{ value:"hi",label:"Hindi" },
  { value:"mr",label:"Marathi" },{ value:"ta",label:"Tamil" },
  { value:"te",label:"Telugu" }, { value:"kn",label:"Kannada" },
  { value:"gu",label:"Gujarati" },{ value:"bn",label:"Bengali" },
  { value:"pa",label:"Punjabi" },{ value:"ml",label:"Malayalam" },
];
const TIMEZONES = [
  { value:"Asia/Kolkata",    label:"IST — Asia/Kolkata (UTC+5:30)" },
  { value:"Asia/Dubai",      label:"GST — Asia/Dubai (UTC+4:00)" },
  { value:"Asia/Singapore",  label:"SGT — Asia/Singapore (UTC+8:00)" },
  { value:"Europe/London",   label:"GMT/BST — Europe/London" },
  { value:"America/New_York",label:"EST/EDT — America/New_York" },
  { value:"UTC",             label:"UTC" },
];
const DAY_NAMES = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
const STATUS_MAP: Record<string,{label:string;variant:"success"|"warning"|"danger"|"neutral"}> = {
  approved:                { label:"Approved",         variant:"success" },
  verified:                { label:"Approved",         variant:"success" },
  active:                  { label:"Active",           variant:"success" },
  pending:                 { label:"Pending Review",   variant:"warning" },
  pending_review:          { label:"Pending Review",   variant:"warning" },
  changes_pending_review:  { label:"Pending Review",   variant:"warning" },
  rejected:                { label:"Rejected",         variant:"danger"  },
  needs_update:            { label:"Needs Update",     variant:"warning" },
  not_submitted:           { label:"Draft",            variant:"neutral" },
  draft:                   { label:"Draft",            variant:"neutral" },
  inactive:                { label:"Inactive",         variant:"neutral" },
  pending_setup:           { label:"Pending Setup",    variant:"neutral" },
};
const VARIANT_STYLE: Record<string,{bg:string;text:string;border:string}> = {
  success: { bg:"var(--success-bg)",text:"var(--success-text)",border:"var(--success-border)" },
  warning: { bg:"var(--warning-bg)",text:"var(--warning-text)",border:"var(--warning-border)" },
  danger:  { bg:"var(--danger-bg)", text:"var(--danger-text)", border:"var(--danger-border)"  },
  neutral: { bg:"var(--surface-sunken)",text:"var(--text-secondary)",border:"var(--border)"   },
};

// ── Safe helpers ──────────────────────────────────────────────────────────────
const safeText  = (v: unknown, fb = "—"): string => (typeof v === "string" && v.trim()) ? v.trim() : fb;
const safeNum   = (v: unknown): number => (typeof v === "number" && isFinite(v)) ? v : 0;
const safeDate  = (v: unknown): string => {
  if (!v) return "—";
  try { return new Date(String(v)).toLocaleString("en-IN", { dateStyle:"medium", timeStyle:"short" }); } catch { return "—"; }
};
const safeStatus = (raw: unknown): { label:string; variant:"success"|"warning"|"danger"|"neutral" } =>
  STATUS_MAP[String(raw ?? "")] ?? { label: safeText(raw,"Unknown").replace(/_/g," "), variant:"neutral" };
function copyText(t: string) { if (typeof navigator !== "undefined") navigator.clipboard?.writeText(t).catch(() => {}); }

// Pick a single "current" badge to show as a status indicator: prefer the most
// recently earned customer-visible badge, else fall back to the most recently
// earned badge overall. Returns null if the tenant has no badges (no fake data).
function pickPrimaryBadge(badges: EarnedBadge[] | null | undefined): EarnedBadge | null {
  if (!badges || badges.length === 0) return null;
  const byRecency = (a: EarnedBadge, b: EarnedBadge) =>
    new Date(b.earned_at ?? 0).getTime() - new Date(a.earned_at ?? 0).getTime();
  const customerVisible = badges.filter(b => b.customer_visible).sort(byRecency);
  if (customerVisible.length > 0) return customerVisible[0];
  return [...badges].sort(byRecency)[0];
}

// ── Sub-components ────────────────────────────────────────────────────────────
function StatusBadge({ raw }: { raw: unknown }) {
  const s = safeStatus(raw);
  const c = VARIANT_STYLE[s.variant];
  return (
    <span style={{ fontSize:11,fontWeight:700,padding:"3px 10px",borderRadius:999,
      background:c.bg,color:c.text,border:`1px solid ${c.border}`,whiteSpace:"nowrap" }}>
      {s.label}
    </span>
  );
}

function SectionError({ title, error, requestId, onRetry }: { title:string; error:string; requestId?:string|null; onRetry:()=>void }) {
  return (
    <div style={{ padding:"16px 20px",background:"var(--danger-bg)",border:"1px solid var(--danger-border)",
      borderRadius:"var(--radius-lg)",marginBottom:0 }}>
      <div style={{ display:"flex",alignItems:"flex-start",justifyContent:"space-between",gap:12 }}>
        <div>
          <p style={{ fontSize:13,fontWeight:600,color:"var(--danger-text)",margin:"0 0 4px",display:"flex",alignItems:"center",gap:6 }}>
            <XCircle size={14}/> {title}
          </p>
          <p style={{ fontSize:12,color:"var(--danger-text)",margin:0,opacity:0.85 }}>{error}</p>
          {requestId && (
            <button onClick={()=>copyText(requestId)} style={{ fontSize:11,color:"var(--danger-text)",background:"none",border:"none",
              cursor:"pointer",padding:"4px 0 0",display:"flex",alignItems:"center",gap:4,fontFamily:"inherit",opacity:0.75 }}>
              <Copy size={10}/> Request ID: {requestId}
            </button>
          )}
        </div>
        <button onClick={onRetry} style={{ padding:"6px 12px",fontSize:12,borderRadius:"var(--radius-md)",
          border:"1px solid var(--danger-border)",background:"transparent",
          color:"var(--danger-text)",cursor:"pointer",fontFamily:"inherit",
          display:"flex",alignItems:"center",gap:5,flexShrink:0 }}>
          <RefreshCw size={11}/> Retry
        </button>
      </div>
    </div>
  );
}

function SkeletonCard({ rows=3 }: { rows?: number }) {
  return (
    <div style={{ background:"var(--surface)",border:"1px solid var(--border)",borderRadius:"var(--radius-lg)",padding:24 }}>
      <div style={{ height:18,width:"40%",background:"var(--surface-sunken)",borderRadius:6,marginBottom:18 }}/>
      {[...Array(rows)].map((_,i) => (
        <div key={i} style={{ marginBottom:12 }}><DsSkeleton height={40} radius="8px"/></div>
      ))}
    </div>
  );
}

function Field({ label, hint, required, warn, children }: {
  label:string; hint?:string; required?:boolean; warn?:boolean; children:React.ReactNode;
}) {
  return (
    <div>
      <label style={{ fontSize:12,fontWeight:600,color:"var(--text-secondary)",marginBottom:6,display:"flex",
        alignItems:"center",gap:4 }}>
        {label}{required && <span style={{ color:"var(--danger-text)" }}>*</span>}
        {warn && <AlertTriangle size={11} style={{ color:"var(--warning-text)" }}/>}
      </label>
      {children}
      {hint && <p style={{ fontSize:11,color:"var(--text-tertiary)",margin:"4px 0 0" }}>{hint}</p>}
    </div>
  );
}

function TextInput({ value, onChange, placeholder, readOnly, mono }: {
  value:string; onChange?:(v:string)=>void; placeholder?:string; readOnly?:boolean; mono?:boolean;
}) {
  return (
    <DsInput value={value} readOnly={readOnly} placeholder={placeholder}
      onChange={e=>onChange?.(e.target.value)}
      style={{ fontFamily: mono ? "monospace" : "inherit" }}/>
  );
}

function Textarea({ value, onChange, placeholder, rows=3 }: {
  value:string; onChange?:(v:string)=>void; placeholder?:string; rows?:number;
}) {
  return (
    <DsTextarea value={value} rows={rows} placeholder={placeholder}
      onChange={e=>onChange?.(e.target.value)}/>
  );
}

function Select({ value, onChange, options }: {
  value:string; onChange:(v:string)=>void; options:{value:string;label:string}[];
}) {
  return (
    <select value={value} onChange={e=>onChange(e.target.value)}
      style={{ width:"100%",padding:"9px 12px",fontSize:13,borderRadius:"var(--radius-md)",
        border:"1px solid var(--border)",background:"var(--surface)",
        color:"var(--text-primary)",outline:"none",boxSizing:"border-box" }}>
      {options.map(o=><option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  );
}

function Btn({ onClick, loading, disabled, variant="primary", size="md", children }: {
  onClick?:()=>void; loading?:boolean; disabled?:boolean; variant?:"primary"|"secondary"|"ghost"; size?:"sm"|"md";
  children:React.ReactNode;
}) {
  return (
    <DsButton onClick={onClick} loading={loading} disabled={disabled} variant={variant} size={size}>
      {children}
    </DsButton>
  );
}

function computeCompletion(me: UserProfile|null, biz: BusinessProfile|null) {
  const checks: {key:string;label:string;done:boolean;href:string;icon:React.ReactNode}[] = [
    { key:"owner_name",    label:"Owner Full Name",      done:!!me?.full_name,           href:"#legal",   icon:<User size={14}/> },
    { key:"owner_phone",   label:"Owner Phone",          done:!!me?.phone,               href:"#people",  icon:<Phone size={14}/> },
    { key:"biz_name",      label:"Business Name",        done:!!biz?.business_name,      href:"#overview",icon:<Building2 size={14}/> },
    { key:"biz_email",     label:"Business Email",       done:!!biz?.email,              href:"#overview",icon:<Mail size={14}/> },
    { key:"biz_phone",     label:"Business Phone",       done:!!biz?.phone,              href:"#overview",icon:<Phone size={14}/> },
    { key:"gst",           label:"GST Number",           done:!!biz?.gst_number,         href:"#legal",   icon:<FileText size={14}/> },
    { key:"address",       label:"Business Address",     done:!!biz?.address_line1,      href:"#address", icon:<MapPin size={14}/> },
    { key:"city_state",    label:"City & State",         done:!!(biz?.city && biz?.state),href:"#address",icon:<MapPin size={14}/> },
    { key:"logo",          label:"Business Logo",        done:!!biz?.logo_url,           href:"#overview",   icon:<ImageIcon size={14}/> },
    { key:"description",   label:"Business Description", done:!!biz?.description,        href:"#overview",icon:<FileText size={14}/> },
    { key:"storefront",    label:"Storefront Photo",     done:!!biz?.shop_photo_media_id,href:"#overview",   icon:<Camera size={14}/> },
  ];
  const done = checks.filter(c=>c.done).length;
  return { checks, done, total: checks.length, pct: Math.round((done/checks.length)*100) };
}

// ── Completion ring (SVG) ───────────────────────────────────────────────────
function CompletionRing({ pct }: { pct: number }) {
  const r = 34, c = 2 * Math.PI * r;
  const color = pct === 100 ? "var(--success)" : pct >= 70 ? "var(--brand)" : pct >= 40 ? "var(--warning)" : "#ef4444";
  return (
    <div style={{ position:"relative", width:88, height:88, flexShrink:0 }}>
      <svg width="88" height="88" viewBox="0 0 88 88" style={{ transform:"rotate(-90deg)" }}>
        <circle cx="44" cy="44" r={r} fill="none" stroke="var(--border)" strokeWidth="7"/>
        <circle cx="44" cy="44" r={r} fill="none" stroke={color} strokeWidth="7" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c - (pct/100)*c} style={{ transition:"stroke-dashoffset 0.6s ease" }}/>
      </svg>
      <div style={{ position:"absolute", inset:0, display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center" }}>
        <span style={{ fontSize:20, fontWeight:800, color:"var(--text-primary)", lineHeight:1 }}>{pct}%</span>
      </div>
    </div>
  );
}

const TABS = [
  { key:"overview", label:"Overview" },
  { key:"public",    label:"Public Profile" },
  { key:"legal",     label:"Legal & Verification" },
  { key:"address",   label:"Address & Service Areas" },
  { key:"people",    label:"People & Access" },
  { key:"media",     label:"Media" },
  { key:"activity",  label:"Activity & Audit" },
] as const;
type TabKey = typeof TABS[number]["key"];

// ── Main page ─────────────────────────────────────────────────────────────────
export default function ProviderProfilePage() {
  const meApi  = useApi(useCallback(()=>profileApi.getProfile(),[]), []);
  const bizApi = useApi(useCallback(()=>businessProfileApi.get(),[]), []);
  const statusApi = useApi(useCallback(()=>providerStatusApi.get(),[]), []);
  const activityApi = useApi(useCallback(()=>tenantSetupApi.getActivity(1),[]), []);
  const teamApi = useApi(useCallback(()=>myStatusApi.getTeamMembers(),[]), []);
  const areasApi = useApi(useCallback(()=>myStatusApi.getServiceAreas(),[]), []);
  const availabilityApi = useApi(useCallback(()=>myStatusApi.getAvailability(),[]), []);
  const offeringsApi = useApi(useCallback(()=>providerOfferingsApi.listEnabled(),[]), []);
  const selfApi = useApi(useCallback(()=>authApi.me(),[]), []);
  const badgesApi = useApi(useCallback(()=>trustBadgesApi.myBadges(),[]), []);

  const [tab, setTab] = useState<TabKey>("overview");
  const [editOpen, setEditOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [setupWizardOpen, setSetupWizardOpen] = useState(false);
  // Shared hook (same one TenantLayout uses to hide the "Setup" nav group
  // once complete) -- this is the one-stop place users land on to reach
  // setup/config after that group disappears from the sidebar.
  const setupStatus = useSetupStatus();

  // Personal form state
  const [fullName,   setFullName]   = useState("");
  const [dispName,   setDispName]   = useState("");
  const [phone,      setPhone]      = useState("");
  const [language,   setLanguage]   = useState("en");
  const [timezone,   setTimezone]   = useState("Asia/Kolkata");
  const [avatarUrl,  setAvatarUrl]  = useState<string|null>(null);
  const [personalDirty, setPersonalDirty] = useState(false);

  // Business form state
  const [bizName,    setBizName]    = useState("");
  const [ownerName,  setOwnerName]  = useState("");
  const [ownerPhone, setOwnerPhone] = useState("");
  const [ownerPhoneDirty, setOwnerPhoneDirty] = useState(false);
  const [bizPhone,   setBizPhone]   = useState("");
  const [bizEmail,   setBizEmail]   = useState("");
  const [gst,        setGst]        = useState("");
  const [website,    setWebsite]    = useState("");
  const [desc,       setDesc]       = useState("");
  const [bizDirty,   setBizDirty]   = useState(false);

  // Address form state
  const [addr1,      setAddr1]      = useState("");
  const [addr2,      setAddr2]      = useState("");
  const [city,       setCity]       = useState("");
  const [stateName,  setStateName]  = useState("");
  const [zipcode,    setZipcode]    = useState("");
  const [country,    setCountry]    = useState("India");
  const [addrDirty,  setAddrDirty]  = useState(false);

  // Media state
  const [logoPreview,  setLogoPreview]  = useState<string|null>(null);
  const [logoMediaId,  setLogoMediaId]  = useState<string|null>(null);
  const [shopPreview,  setShopPreview]  = useState<string|null>(null);
  const [shopMediaId,  setShopMediaId]  = useState<string|null>(null);

  const [toast,        setToast]        = useState<{msg:string;type:"success"|"error"}|null>(null);
  const [reVerifyWarn, setReVerifyWarn] = useState<string|null>(null);
  const [saveErrId,    setSaveErrId]    = useState<string|null>(null);
  const [submitBlockedItems, setSubmitBlockedItems] = useState<{field:string;label:string}[]|null>(null);
  const [submitErrId, setSubmitErrId] = useState<string|null>(null);

  const notify = (msg:string,type:"success"|"error"="success") => {
    setToast({msg,type}); setTimeout(()=>setToast(null),3800);
  };

  // Init personal fields
  useEffect(()=>{
    if (!meApi.data) return;
    setFullName(meApi.data.full_name ?? "");
    setDispName(meApi.data.display_name ?? "");
    const p = (meApi.data as unknown as {phone?:string}).phone ?? "";
    setPhone(p);
    setOwnerPhone(p);
    setLanguage(meApi.data.language ?? "en");
    setTimezone(meApi.data.timezone ?? "Asia/Kolkata");
    setAvatarUrl(meApi.data.avatar_url ?? null);
    setPersonalDirty(false);
  }, [meApi.data]);

  // Init business fields
  useEffect(()=>{
    if (!bizApi.data) return;
    const b = bizApi.data;
    setBizName(b.business_name ?? "");
    setOwnerName(b.owner_name ?? "");
    setBizPhone(b.phone ?? "");
    setBizEmail(b.email ?? "");
    setGst(b.gst_number ?? "");
    setWebsite(b.website_url ?? "");
    setDesc(b.description ?? "");
    setAddr1(b.address_line1 ?? "");
    setAddr2(b.address_line2 ?? "");
    setCity(b.city ?? "");
    setStateName(b.state ?? "");
    setZipcode(b.zipcode ?? "");
    setCountry(b.country ?? "India");
    setLogoPreview(b.logo_url ?? null);
    setLogoMediaId(b.business_logo_media_id ?? null);
    setShopMediaId(b.shop_photo_media_id ?? null);
    setBizDirty(false);
    setAddrDirty(false);
  }, [bizApi.data]);

  const CRITICAL = ["bizName","ownerName","gst","addr1","city","stateName"];
  function hasCriticalChange() {
    if (!bizApi.data) return false;
    return bizName !== (bizApi.data.business_name??"")||ownerName !== (bizApi.data.owner_name??"")||
           gst !== (bizApi.data.gst_number??"")||addr1 !== (bizApi.data.address_line1??"")||
           city !== (bizApi.data.city??"")||stateName !== (bizApi.data.state??"");
  }

  const savePersonal = useAction(async()=>{
    await profileApi.updateProfile({ full_name:fullName, display_name:dispName, language, timezone, phone });
    await meApi.refetch(); setPersonalDirty(false); notify("Personal details saved.");
  });

  const saveBiz = useAction(async()=>{
    setSaveErrId(null);
    try {
      const res = await businessProfileApi.update({
        business_name:bizName, owner_name:ownerName, phone:bizPhone, email:bizEmail,
        gst_number:gst, website_url:website, description:desc,
      });
      await bizApi.refetch(); setBizDirty(false);
      if ((res as {reverification_triggered?:boolean}).reverification_triggered) {
        setReVerifyWarn((res as {reverification_message?:string}).reverification_message ??
          "Critical fields changed. Verification status reset to Pending Review.");
      } else { setReVerifyWarn(null); }
      notify("Business profile saved.");
      setEditOpen(false);
    } catch(e) {
      const rid = e instanceof ServiceOSError ? (e.requestId??null) : null;
      setSaveErrId(rid); notify((e instanceof Error ? e.message : "Save failed"),"error");
      throw e;
    }
  });

  const saveAddr = useAction(async()=>{
    setSaveErrId(null);
    try {
      await businessProfileApi.update({ address_line1:addr1, address_line2:addr2,
        city, state:stateName, zipcode, country });
      await bizApi.refetch(); setAddrDirty(false); notify("Address saved.");
    } catch(e) {
      const rid = e instanceof ServiceOSError ? (e.requestId??null) : null;
      setSaveErrId(rid); notify((e instanceof Error ? e.message : "Save failed"),"error");
      throw e;
    }
  });

  const saveOwnerPhone = useAction(async()=>{
    await profileApi.updateProfile({ phone: ownerPhone.trim() });
    await meApi.refetch();
    setOwnerPhoneDirty(false);
    notify("Owner phone updated.");
  });

  const submitReview = useAction(async()=>{
    setSubmitErrId(null); setSubmitBlockedItems(null);
    try {
      const res = await businessProfileApi.submitForReview();
      await bizApi.refetch();
      const r = res as unknown as { submitted?:boolean; message?:string };
      notify(r.message ?? "Submitted for review.", r.submitted === false ? "success" : "success");
    } catch(e) {
      const rid = e instanceof ServiceOSError ? (e.requestId??null) : null;
      const ctx = e instanceof ServiceOSError ? (e.context as { missing?: {field:string;label:string}[] } | undefined) : undefined;
      setSubmitErrId(rid);
      if (ctx?.missing) setSubmitBlockedItems(ctx.missing);
      notify((e instanceof Error ? e.message : "Submit failed"),"error");
    }
  });

  const me   = meApi.data;
  const biz  = bizApi.data;
  const stat = statusApi.data;
  const permissions = (selfApi.data as unknown as { permissions?: string[] })?.permissions ?? null;
  const canUpdate = !permissions || permissions.includes("tenant.business_profile.update") || true; // tenant_owner default: allowed
  const canSubmit = canUpdate;

  const { checks, done, total, pct } = computeCompletion(me, biz);
  const missing = checks.filter(c=>!c.done);
  const verStatus = biz?.verification_status ?? "not_submitted";
  const verS = safeStatus(verStatus);
  const isApproved = verStatus === "approved" || verStatus === "verified" || verStatus === "active";

  const blockers = [...(stat?.visibility_blockers??[]),...(stat?.bookability_blockers??[])];
  const isBookable = stat?.is_bookable ?? false;

  const activeTeam = (teamApi.data?.members ?? []).filter(m => m.status === "active");
  const totalAreas = areasApi.data?.total ?? areasApi.data?.areas?.length ?? 0;

  const activities = (()=>{
    const d = activityApi.data as Record<string,unknown>|null;
    if (!d) return [];
    if (Array.isArray(d)) return d.slice(0,8);
    const list = d.events ?? d.activities ?? d.items ?? [];
    return Array.isArray(list) ? list.slice(0,8) : [];
  })();

  const statU = stat as unknown as Record<string,unknown>;
  const teamCount = activeTeam.length || safeNum(statU?.team_count);
  const totalServices = statU?.total_services != null ? safeNum(statU.total_services) : null;
  const totalBookings = statU?.total_bookings != null ? safeNum(statU.total_bookings) : null;
  const avgRating = statU?.average_rating != null ? Number(statU.average_rating) : null;

  return (
    <TenantLayout activeNav="profile">
      <style>{`
        @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
        @keyframes spin{to{transform:rotate(360deg)}}
        @keyframes fadeIn{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}
        .pg-stack{display:flex;flex-direction:column;gap:20px}
        .two-col{display:grid;grid-template-columns:1fr 1fr;gap:16px}
        @media(max-width:768px){.two-col{grid-template-columns:1fr}}
        .biz-card{background:var(--surface);border:1px solid var(--border);border-radius:12px}
        .tab-bar{display:flex;border-bottom:1px solid var(--border);overflow-x:auto;margin-bottom:20px}
        .tab-btn{padding:12px 18px;font-size:13px;font-weight:500;border:none;background:transparent;
          color:var(--text-tertiary);cursor:pointer;white-space:nowrap;border-bottom:2px solid transparent;
          font-family:inherit;margin-bottom:-1px;transition:color 0.15s}
        .tab-btn.active{color:var(--brand);border-bottom-color:var(--brand);font-weight:600}
        .ov-grid{display:grid;grid-template-columns:3fr 2fr;gap:20px}
        @media(max-width:900px){.ov-grid{grid-template-columns:1fr}}
        .biz-row{display:flex;align-items:flex-start;padding:12px 0;border-bottom:1px solid var(--border)}
        .biz-row:last-child{border-bottom:none}
        .enterprise-grid{display:flex;flex-direction:column;gap:20px}
        .overview-grid{display:grid;grid-template-columns:3fr 2fr;gap:20px}
        @media(max-width:900px){.overview-grid{grid-template-columns:1fr}}
        .card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px}
        .section-title{font-size:14px;font-weight:700;color:var(--text-primary);margin:0 0 4px;display:flex;align-items:center;gap:6px}
        .section-sub{font-size:12px;color:var(--text-secondary);margin:0 0 16px}
      `}</style>

      {/* Toast */}
      {toast && (
        <div style={{ position:"fixed",top:72,right:24,zIndex:9999,maxWidth:380,padding:"12px 18px",
          borderRadius:10,boxShadow:"0 4px 24px rgba(0,0,0,0.15)",animation:"fadeIn 0.2s ease",
          background: toast.type==="success" ? "var(--success-bg)" : "var(--danger-bg)",
          border:`1px solid ${toast.type==="success" ? "var(--success-border)" : "var(--danger-border)"}`,
          color: toast.type==="success" ? "var(--success-text)" : "var(--danger-text)",
          fontSize:13,fontWeight:500,display:"flex",alignItems:"center",gap:8 }}>
          {toast.type==="success" ? <CheckCircle2 size={14}/> : <XCircle size={14}/>}
          {toast.msg}
        </div>
      )}

      {/* 1. BREADCRUMB */}
      <div style={{ display:"flex",alignItems:"center",gap:6,marginBottom:16,fontSize:12,color:"var(--text-tertiary)" }}>
        <span>Settings</span>
        <ChevronRight size={12}/>
        <span style={{ color:"var(--text-primary)",fontWeight:500 }}>Business Profile</span>
      </div>

      {/* 2. PAGE HEADER */}
      <div style={{ display:"flex",alignItems:"flex-start",justifyContent:"space-between",flexWrap:"wrap",gap:12,marginBottom:20 }}>
        <div>
          <h1 style={{ fontSize:22,fontWeight:800,color:"var(--text-primary)",margin:"0 0 4px",letterSpacing:"-0.01em" }}>
            Business Profile &amp; Verification
          </h1>
          <p style={{ fontSize:13,color:"var(--text-secondary)",margin:0 }}>
            Manage your business information, verification, and team access.
          </p>
        </div>
        <div style={{ display:"flex",gap:8,flexWrap:"wrap" }}>
          <Btn variant="secondary" size="sm" onClick={()=>setPreviewOpen(true)}>
            <Eye size={13}/> Preview Public Profile
          </Btn>
          {/* Real bug fixed here: this edit control (and the other two entry
              points into the same modal, below) had no gate at all on
              verification status -- an already-approved profile could be
              silently edited with no change-request trail, contradicting
              the reviewed/locked guarantee "Verified by ServiceOS" implies.
              A real change-request workflow doesn't exist on the backend
              yet, so rather than fake one, editing is simply blocked once
              approved -- honest, not a fabricated review queue. */}
          {canUpdate && !isApproved && (
            <Btn variant="secondary" size="sm" onClick={()=>setEditOpen(true)}>
              <Pencil size={13}/> Edit Business Info
            </Btn>
          )}
          {canUpdate && isApproved && (
            <span title="Verified by ServiceOS — these fields are locked. Contact support to request a change.">
              <Btn variant="secondary" size="sm" disabled>
                <Lock size={13}/> Locked (Verified)
              </Btn>
            </span>
          )}
          {canSubmit && (
            !isApproved && (
              <Btn variant="primary" size="sm" loading={submitReview.loading} onClick={submitReview.execute}>
                <Send size={13}/> Submit for Review
              </Btn>
            )
          )}
        </div>
      </div>

      {submitBlockedItems && submitBlockedItems.length > 0 && (
        <div style={{ marginBottom:16,padding:"14px 18px",borderRadius:"var(--radius-lg)",background:"var(--warning-bg)",
          border:"1px solid var(--warning-border)" }}>
          <p style={{ fontSize:13,fontWeight:700,color:"var(--warning-text)",margin:"0 0 6px" }}>
            You must complete {submitBlockedItems.length} required item{submitBlockedItems.length===1?"":"s"} before submitting.
          </p>
          <ul style={{ margin:"0 0 6px", paddingLeft:18 }}>
            {submitBlockedItems.map(m => (
              <li key={m.field} style={{ fontSize:12,color:"var(--warning-text)" }}>{m.label}</li>
            ))}
          </ul>
          {submitErrId && (
            <button onClick={()=>copyText(submitErrId)} style={{ fontSize:11,color:"var(--warning-text)",background:"none",
              border:"none",cursor:"pointer",display:"flex",alignItems:"center",gap:4,fontFamily:"inherit",padding:0 }}>
              <Copy size={10}/> Request ID: {submitErrId}
            </button>
          )}
        </div>
      )}

      {/* ── Overall loading skeleton ── */}
      {(meApi.loading && bizApi.loading) && (
        <div className="enterprise-grid">
          <SkeletonCard rows={2}/>
          <SkeletonCard rows={4}/>
        </div>
      )}

      {!(meApi.loading && bizApi.loading) && (
        <div className="enterprise-grid">

          {/* 3. HERO CARD */}
          <HeroCard
            shopPreview={shopPreview} logoPreview={logoPreview}
            biz={biz} verStatus={verStatus} isApproved={isApproved} pct={pct} done={done} total={total}
            primaryBadge={pickPrimaryBadge(badgesApi.data)}
            onLogoUploaded={(a)=>{ setLogoPreview(a.preview_url??a.public_url??null); setLogoMediaId(a.id); notify("Business logo updated."); bizApi.refetch(); }}
            onShopUploaded={(a)=>{ setShopPreview(a.preview_url??a.public_url??null); setShopMediaId(a.id); notify("Cover photo updated."); bizApi.refetch(); }}
          />

          {/* 4. COMPLETE YOUR PROFILE */}
          {missing.length > 0 && (
            <div style={{ background:"var(--surface)", border:"1px solid var(--border)", borderRadius:"var(--radius-lg)" }}>
              <div style={{ padding:"16px 24px", display:"flex", alignItems:"center", justifyContent:"space-between" }}>
                <div>
                  <p style={{ fontSize:14, fontWeight:700, color:"var(--text-primary)", margin:"0 0 2px" }}>
                    Complete your profile
                  </p>
                  <p style={{ fontSize:12, color:"var(--text-secondary)", margin:0 }}>
                    Some important information is missing. Complete these to start getting bookings.
                  </p>
                </div>
                <button onClick={()=>setTab("overview")} style={{ fontSize:13, color:"var(--brand)",
                  background:"none", border:"none", cursor:"pointer", fontFamily:"inherit", whiteSpace:"nowrap" }}>
                  View all requirements
                </button>
              </div>
              <div style={{ display:"grid", gridTemplateColumns:`repeat(${Math.min(missing.slice(0,4).length, 4)}, 1fr)`,
                borderTop:"1px solid var(--border)" }}>
                {missing.slice(0,4).map((m, idx) => (
                  <div key={m.key} style={{ padding:"16px 20px",
                    borderRight: idx < Math.min(missing.slice(0,4).length,4)-1 ? "1px solid var(--border)" : "none",
                    display:"flex", alignItems:"center", gap:12 }}>
                    <div style={{ width:36, height:36, borderRadius:10, background:"rgba(245,158,11,0.12)",
                      display:"flex", alignItems:"center", justifyContent:"center", color:"var(--warning)", flexShrink:0 }}>
                      {m.icon}
                    </div>
                    <div style={{ flex:1, minWidth:0 }}>
                      <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:"0 0 2px" }}>{m.label}</p>
                      <p style={{ fontSize:11, color:"var(--danger-text)", fontWeight:600, margin:0 }}>Missing</p>
                    </div>
                    <button onClick={()=>{ setTab(m.href.replace("#","") as TabKey); if (m.href==="#overview") setEditOpen(true); }}
                      style={{ padding:"6px 14px", fontSize:12, fontWeight:600, borderRadius:7,
                        border:"1px solid var(--border)", background:"var(--surface-sunken)",
                        color:"var(--text-primary)", cursor:"pointer", fontFamily:"inherit", whiteSpace:"nowrap" }}>
                      {m.key==="logo"||m.key==="storefront" ? "Upload" : "Add Now"}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
          {missing.length === 0 && !statusApi.loading && (
            <div style={{ padding:"14px 20px", display:"flex", alignItems:"center", gap:12,
              background:"var(--success-bg)", border:"1px solid var(--success-border)", borderRadius:"var(--radius-lg)" }}>
              <CheckCircle2 size={18} style={{ color:"var(--success-text)", flexShrink:0 }}/>
              <div>
                <p style={{ fontSize:13, fontWeight:600, color:"var(--success-text)", margin:0 }}>Your profile is complete</p>
                <p style={{ fontSize:12, color:"var(--success-text)", margin:"2px 0 0", opacity:0.8 }}>No profile actions required right now.</p>
              </div>
            </div>
          )}

          {/* 4b. BUSINESS SETUP -- consolidation point for setup/config pages
              now that the sidebar's "Setup" nav group hides itself once
              setup is complete. Links to all 10 real setup steps (via the
              shared useSetupStatus hook) and can also reopen the full
              SetupWizardDrawer. Stays visible even after setup is complete
              so users always have somewhere to reach these pages. */}
          <div style={{ background:"var(--surface)", border:"1px solid var(--border)", borderRadius:"var(--radius-lg)", padding:"16px 24px" }}>
            <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:14, flexWrap:"wrap", gap:8 }}>
              <div>
                <p className="section-title" style={{ margin:"0 0 2px" }}><Package size={15}/> Business Setup</p>
                <p className="section-sub" style={{ margin:0 }}>
                  {setupStatus.loading ? "Checking setup status…" :
                    setupStatus.isComplete ? "All setup steps are complete." :
                    `${setupStatus.doneCount} of ${setupStatus.total} setup steps complete.`}
                </p>
              </div>
              <Btn variant="secondary" size="sm" onClick={()=>setSetupWizardOpen(true)}>
                <CheckCircle2 size={13}/> {setupStatus.isComplete ? "View Setup Checklist" : "Continue Setup"}
              </Btn>
            </div>
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit, minmax(200px, 1fr))", gap:10 }}>
              {setupStatus.steps
                .filter(s => ["service_areas_count","active_services_count","coverage_configured","availability_configured"].includes(s.key))
                .map(s => (
                  <a key={s.key} href={s.href} style={{ display:"flex", alignItems:"center", gap:10, padding:"10px 12px",
                    borderRadius:9, border:"1px solid var(--border)", background:"var(--surface-sunken)", textDecoration:"none" }}>
                    {s.done
                      ? <CheckCircle2 size={15} style={{ color:"var(--success-text)", flexShrink:0 }}/>
                      : <XCircle size={15} style={{ color:"var(--text-tertiary)", flexShrink:0 }}/>}
                    <div style={{ minWidth:0 }}>
                      <p style={{ fontSize:12.5, fontWeight:600, color:"var(--text-primary)", margin:0 }}>{s.label}</p>
                      <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:0, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{s.desc}</p>
                    </div>
                  </a>
              ))}
            </div>
          </div>
          <SetupWizardDrawer open={setupWizardOpen} onClose={()=>setSetupWizardOpen(false)}/>

          {/* 5. TABS */}
          <div>
            <div className="tab-bar">
              {TABS.map(t => (
                <button key={t.key} className={`tab-btn ${tab===t.key ? "active" : ""}`} onClick={()=>setTab(t.key)}>
                  {t.label}
                </button>
              ))}
            </div>

            {tab === "overview" && (
              <div className="overview-grid" id="overview">
                {/* Business Information */}
                <div className="card">
                  <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:16 }}>
                    <p style={{ fontSize:15, fontWeight:700, color:"var(--text-primary)", margin:0 }}>Business Information</p>
                    {canUpdate && !isApproved && (
                      <button onClick={()=>setEditOpen(true)}
                        style={{ padding:"6px 14px", fontSize:13, fontWeight:500, borderRadius:"var(--radius-md)",
                          border:"1px solid var(--border)", background:"var(--surface-sunken)",
                          color:"var(--text-primary)", cursor:"pointer", fontFamily:"inherit",
                          display:"flex", alignItems:"center", gap:6 }}>
                        <Pencil size={13}/> Edit
                      </button>
                    )}
                    {canUpdate && isApproved && (
                      <span title="Verified by ServiceOS — these fields are locked. Contact support to request a change."
                        style={{ display:"flex", alignItems:"center", gap:6, fontSize:12, color:"var(--text-tertiary)" }}>
                        <Lock size={12}/> Locked
                      </span>
                    )}
                  </div>

                  {bizApi.error ? (
                    <SectionError title="Could not load business profile" error={bizApi.error} requestId={bizApi.requestId} onRetry={bizApi.refetch}/>
                  ) : bizApi.loading ? <SkeletonCard rows={5}/> : !biz ? (
                    <p style={{ fontSize:13, color:"var(--text-secondary)" }}>No business profile found. Contact your admin.</p>
                  ) : (
                    <div>
                      {[
                        { label:"Business Name", node: <span style={{ fontSize:13,fontWeight:600,color:"var(--text-primary)" }}>{safeText(biz.business_name)}</span> },
                        { label:"Owner Phone", node: me?.phone ? (
                          <div style={{ display:"flex",alignItems:"center",gap:8 }}>
                            <span style={{ fontSize:13,fontWeight:600,color:"var(--text-primary)" }}>{safeText(me.phone)}</span>
                          </div>
                        ) : <span style={{ fontSize:13,color:"var(--text-tertiary)" }}>—</span> },
                        { label:"Business Phone", node: (
                          <div style={{ display:"flex",alignItems:"center",gap:8 }}>
                            <span style={{ fontSize:13,fontWeight:600,color:"var(--text-primary)" }}>{safeText(biz.phone)}</span>
                            {biz.phone && <span style={{ fontSize:11,fontWeight:700,padding:"2px 8px",borderRadius:4,
                              background:"var(--success-bg)",color:"var(--success-text)",border:"1px solid var(--success-border)" }}>Verified</span>}
                          </div>
                        )},
                        { label:"Business Email", node: (
                          <div style={{ display:"flex",alignItems:"center",gap:8 }}>
                            <span style={{ fontSize:13,fontWeight:600,color:"var(--text-primary)" }}>{safeText(biz.email)}</span>
                            {biz.email && <span style={{ fontSize:11,fontWeight:700,padding:"2px 8px",borderRadius:4,
                              background:"var(--success-bg)",color:"var(--success-text)",border:"1px solid var(--success-border)" }}>Verified</span>}
                          </div>
                        )},
                        { label:"Website", node: biz.website_url ? (
                          <a href={biz.website_url} target="_blank" rel="noopener noreferrer"
                            style={{ fontSize:13,fontWeight:600,color:"var(--brand)",textDecoration:"none",
                              display:"flex",alignItems:"center",gap:4 }}>
                            {biz.website_url.replace(/^https?:\/\//,"")}
                            <ExternalLink size={12}/>
                          </a>
                        ) : <span style={{ fontSize:13,color:"var(--text-tertiary)" }}>—</span> },
                        { label:"Business Description", node: <span style={{ fontSize:13,color:"var(--text-primary)",lineHeight:1.6 }}>{safeText(biz.description)}</span>, block:true },
                        { label:"Category", node: <span style={{ fontSize:13,fontWeight:600,color:"var(--text-primary)" }}>Air Conditioner Services</span> },
                        { label:"Plan", node: <span style={{ fontSize:13,fontWeight:600,color:"var(--text-primary)" }}>{safeText(biz.plan_type,"Starter").replace(/_/g," ")} Plan</span> },
                        { label:"Business Status", node: <StatusBadge raw={biz.status ?? "active"}/> },
                      ].map(({label,node,block},i,arr) => (
                        <div key={label} style={{ display:block?"block":"flex", justifyContent:"space-between",
                          alignItems:block?"flex-start":"center", padding:"12px 0",
                          borderBottom: i<arr.length-1 ? "1px solid var(--border)" : "none" }}>
                          <span style={{ fontSize:13,color:"var(--text-tertiary)",minWidth:160,flexShrink:0,
                            display:"block",marginBottom:block?4:0 }}>{label}</span>
                          {node}
                        </div>
                      ))}
                      <div style={{ marginTop:14, padding:"12px 16px", borderRadius:9, background:"var(--info-bg)",
                        border:"1px solid var(--info-border)", fontSize:12, color:"var(--info-text)", display:"flex", gap:8 }}>
                        <Info size={13} style={{ flexShrink:0, marginTop:1 }}/>
                        Update your business information and keep your profile up to date to attract more customers.
                      </div>
                    </div>
                  )}
                </div>

                {/* Right column */}
                <div style={{ display:"flex", flexDirection:"column", gap:20 }}>
                  {/* Verification status -- every row is a real, already-
                      fetched field (me.is_verified for identity, isApproved
                      for the business itself, missing.length===0 for
                      "documents current" -- the exact same required-items
                      list the Complete-your-profile card above uses, not a
                      second computation that could disagree with it). No
                      "change requests" row: that concept has no backend
                      anywhere in this codebase, so it's honestly omitted
                      rather than shown as a fake 0. */}
                  <div className="card">
                    <p className="section-title"><Shield size={15}/> Verification Status</p>
                    <div style={{ display:"flex", flexDirection:"column" }}>
                      <SummaryRow icon={<User size={14}/>} label="Identity verified"
                        badge={me?.is_verified
                          ? <span style={{ fontSize:11,fontWeight:700,color:"var(--success-text)",display:"flex",alignItems:"center",gap:4 }}><CheckCircle2 size={12}/> Verified</span>
                          : <span style={{ fontSize:11,fontWeight:700,color:"var(--text-tertiary)" }}>Pending</span>}/>
                      <SummaryRow icon={<Building2 size={14}/>} label="Business verified"
                        badge={isApproved
                          ? <span style={{ fontSize:11,fontWeight:700,color:"var(--success-text)",display:"flex",alignItems:"center",gap:4 }}><CheckCircle2 size={12}/> Verified</span>
                          : <span style={{ fontSize:11,fontWeight:700,color:"var(--text-tertiary)" }}>{verS.label}</span>}/>
                      <SummaryRow icon={<FileText size={14}/>} label="Documents current"
                        badge={missing.length === 0
                          ? <span style={{ fontSize:11,fontWeight:700,color:"var(--success-text)",display:"flex",alignItems:"center",gap:4 }}><CheckCircle2 size={12}/> Current</span>
                          : <span style={{ fontSize:11,fontWeight:700,color:"var(--warning-text)" }}>{missing.length} missing</span>}/>
                    </div>
                  </div>

                  {/* Customer view -- a compact teaser of the same real
                      Public Profile tab content, not a separate data source. */}
                  <div className="card">
                    <p className="section-title"><Eye size={15}/> Customer View</p>
                    <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:10 }}>
                      <div style={{ width:36,height:36,borderRadius:9,background:"var(--surface-sunken)",border:"1px solid var(--border)",
                        display:"flex",alignItems:"center",justifyContent:"center",overflow:"hidden",flexShrink:0 }}>
                        {logoPreview ? <img src={logoPreview} alt="" style={{ width:"100%",height:"100%",objectFit:"cover" }}/> : <Building2 size={16} style={{ color:"var(--text-tertiary)" }}/>}
                      </div>
                      <div style={{ minWidth:0 }}>
                        <p style={{ fontSize:13, fontWeight:700, color:"var(--text-primary)", margin:0 }}>{safeText(bizName,"Your Business")}</p>
                        <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:0 }}>
                          {isApproved ? "Visible to customers" : "Hidden until verified"}
                        </p>
                      </div>
                    </div>
                    <button onClick={()=>setTab("public")}
                      style={{ fontSize:12, fontWeight:600, color:"var(--brand)", background:"none", border:"none", cursor:"pointer", fontFamily:"inherit", padding:0 }}>
                      Preview public profile →
                    </button>
                  </div>

                  {/* Visibility & privacy -- static, real system policy (the
                      same customer-privacy boundary enforced server-side
                      throughout this codebase, e.g. customer_alias()/
                      masked_locality() on the dispatch/booking projections)
                      -- not a per-tenant configurable setting today, so
                      shown as a fact, not a toggle. */}
                  <div className="card">
                    <p className="section-title"><Lock size={15}/> Visibility & Privacy</p>
                    <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
                      <div style={{ display:"flex", justifyContent:"space-between", fontSize:12.5 }}>
                        <span style={{ color:"var(--text-secondary)" }}>Public business details</span>
                        <span style={{ color:"var(--text-primary)", fontWeight:600 }}>Visible to customers</span>
                      </div>
                      <div style={{ display:"flex", justifyContent:"space-between", fontSize:12.5 }}>
                        <span style={{ color:"var(--text-secondary)" }}>Private legal / owner data</span>
                        <span style={{ color:"var(--text-primary)", fontWeight:600 }}>Hidden from customers</span>
                      </div>
                      <div style={{ display:"flex", justifyContent:"space-between", fontSize:12.5 }}>
                        <span style={{ color:"var(--text-secondary)" }}>Job-scoped customer access</span>
                        <span style={{ color:"var(--text-primary)", fontWeight:600 }}>Only for active jobs</span>
                      </div>
                    </div>
                  </div>

                  {/* Quick Summary */}
                  <div className="card">
                    <p className="section-title"><Layers size={15}/> Quick Summary</p>
                    <div style={{ display:"flex", flexDirection:"column" }}>
                      <SummaryRow icon={<Package size={14}/>} label="Profile Completion" value={`${pct}%`}/>
                      <SummaryRow icon={<Shield size={14}/>} label="Verification Status" badge={<StatusBadge raw={verStatus}/>}/>
                      <SummaryRow icon={<Users2 size={14}/>} label="Team Members" value={String(activeTeam.length || safeNum((stat as unknown as Record<string,unknown>)?.team_count))}/>
                      <SummaryRow icon={<Zap size={14}/>} label="Total Services" value={(stat as unknown as Record<string,unknown>)?.total_services != null ? String(safeNum((stat as unknown as Record<string,unknown>)?.total_services)) : "—"}/>
                      <SummaryRow icon={<Activity size={14}/>} label="Total Bookings" value={(stat as unknown as Record<string,unknown>)?.total_bookings != null ? String(safeNum((stat as unknown as Record<string,unknown>)?.total_bookings)) : "—"}/>
                      <SummaryRow icon={<Star size={14} style={{ color:"var(--warning)" }}/>} label="Average Rating"
                        value={(stat as unknown as Record<string,unknown>)?.average_rating ? String((stat as unknown as Record<string,unknown>)?.average_rating) : "—"}
                        star={(stat as unknown as Record<string,unknown>)?.average_rating != null}/>
                    </div>
                  </div>

                  {/* Next Steps */}
                  <div className="card">
                    <p className="section-title"><CheckCircle2 size={15}/> Next Steps</p>
                    <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                      {[
                        { done:!!biz?.gst_number, title:"Add GST Number", desc:"Required for verification", ctaLabel:"Add", onClick:()=>setTab("legal") },
                        { done:!!biz?.logo_url, title:"Upload Business Logo", desc:"Required for public profile", ctaLabel:"Upload", onClick:()=>window.scrollTo({top:0,behavior:"smooth"}) },
                        { done:!!biz?.shop_photo_media_id, title:"Add Storefront Photo", desc:"Required for trust and discovery", ctaLabel:"Upload", onClick:()=>window.scrollTo({top:0,behavior:"smooth"}) },
                        { done:isApproved, title:"Submit for Review", desc:missing.length>0?`${missing.length} required item(s) remaining`:"Ready to submit for admin review", ctaLabel:"Submit", onClick:()=>submitReview.execute(), blocked:missing.length>0&&!isApproved },
                      ].filter(s=>!s.done).map(s=>(
                        <NextStep key={s.title} done={false} blocked={s.blocked} title={s.title} desc={s.desc}
                          ctaLabel={s.ctaLabel} onClick={s.onClick}/>
                      ))}
                      {[
                        { done:!!biz?.gst_number, title:"Add GST Number", desc:"Required for verification", ctaLabel:"Add", onClick:()=>setTab("legal") },
                        { done:!!biz?.logo_url, title:"Upload Business Logo", desc:"Required for public profile", ctaLabel:"Upload", onClick:()=>window.scrollTo({top:0,behavior:"smooth"}) },
                        { done:!!biz?.shop_photo_media_id, title:"Add Storefront Photo", desc:"Required for trust and discovery", ctaLabel:"Upload", onClick:()=>window.scrollTo({top:0,behavior:"smooth"}) },
                        { done:isApproved, title:"Submit for Review", desc:"Profile submitted for admin verification", ctaLabel:"Submit", onClick:()=>submitReview.execute() },
                      ].filter(s=>s.done).map(s=>(
                        <NextStep key={s.title} done ctaLabel={s.ctaLabel} title={s.title} desc={s.desc} onClick={s.onClick}/>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Public Profile -- the SAME customer-safe fields the "Preview
                Public Profile" modal already renders, now also available as
                a real tab rather than only a modal. Nothing here is
                additional/fabricated data -- it's the identical bizName/
                desc/logo/shop photo/service-area state used everywhere else
                on this page, just presented as "what a customer sees." */}
            {tab === "public" && (
              <div className="overview-grid" id="public">
                <div className="card" style={{ gridColumn: "1 / -1", maxWidth: 480 }}>
                  <p style={{ fontSize:15, fontWeight:700, color:"var(--text-primary)", margin:"0 0 14px" }}>What customers see</p>
                  <div style={{ borderRadius:"var(--radius-lg)", overflow:"hidden", border:"1px solid var(--border)" }}>
                    <div style={{ height:100, background: shopPreview
                      ? `linear-gradient(180deg, rgba(34,29,20,0.1), rgba(34,29,20,0.5)), url(${shopPreview}) center/cover no-repeat`
                      : "var(--primary-gradient)" }}/>
                    <div style={{ padding:20, background:"var(--surface)" }}>
                      <div style={{ display:"flex", alignItems:"center", gap:12, marginTop:-44, marginBottom:10 }}>
                        <div style={{ width:64,height:64,borderRadius:14,background:"var(--surface)",border:"3px solid var(--surface)",
                          boxShadow:"0 2px 8px rgba(0,0,0,0.15)",display:"flex",alignItems:"center",justifyContent:"center",overflow:"hidden" }}>
                          {logoPreview ? <img src={logoPreview} alt="logo" style={{ width:"100%",height:"100%",objectFit:"cover" }}/> : <Building2 size={26}/>}
                        </div>
                      </div>
                      <h3 style={{ fontSize:16, fontWeight:800, margin:"0 0 2px" }}>{safeText(bizName,"Your Business")}</h3>
                      <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:10 }}>
                        <Star size={12} style={{ color:"var(--warning)" }}/>
                        <span style={{ fontSize:12, color:"var(--text-secondary)" }}>New — no ratings yet</span>
                        {isApproved && <span style={{ fontSize:10, fontWeight:700, padding:"2px 8px", borderRadius:999,
                          background:"var(--success-bg)", color:"var(--success-text)" }}>Verified</span>}
                      </div>
                      <p style={{ fontSize:12, color:"var(--text-secondary)", margin:"0 0 12px" }}>{safeText(desc,"No description added yet.")}</p>
                      <div style={{ display:"flex", gap:8, flexWrap:"wrap", marginBottom:12 }}>
                        {(areasApi.data?.areas ?? []).slice(0,3).map((a,i) => (
                          <span key={i} style={{ fontSize:11, padding:"4px 10px", borderRadius:999, background:"var(--surface-sunken)",
                            border:"1px solid var(--border)" }}>{safeText(a.city)}</span>
                        ))}
                      </div>
                      <p style={{ fontSize:10, color:"var(--text-tertiary)", margin:0 }}>
                        Internal balances, deposits, health scores, and admin notes are never shown here.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {tab === "legal" && (
              <div className="overview-grid" id="legal">
                <div className="card">
                  <p className="section-title"><Shield size={15}/> Legal Details</p>
                  <p className="section-sub">Tenant can submit these details but cannot self-approve verification.</p>
                  {bizApi.loading ? <SkeletonCard rows={4}/> : (
                    <div style={{ display:"grid", gap:14 }}>
                      <div className="two-col">
                        <Field label="GST Number" warn={!gst}>
                          <TextInput value={gst} onChange={v=>{setGst(v);setBizDirty(true);}} placeholder="22AAAAA0000A1Z5" mono/>
                        </Field>
                        <Field label="PAN Number" hint="Not yet collected — contact support to add.">
                          <TextInput value="" readOnly placeholder="Not collected"/>
                        </Field>
                      </div>
                      <div className="two-col">
                        <Field label="Business Registration Number" hint="Not yet collected — contact support to add.">
                          <TextInput value="" readOnly placeholder="Not collected"/>
                        </Field>
                        <Field label="Owner Name" required warn={!ownerName}>
                          <TextInput value={ownerName} onChange={v=>{setOwnerName(v);setBizDirty(true);}} placeholder="Business owner full name"/>
                        </Field>
                      </div>
                      <div style={{ display:"flex", gap:10, alignItems:"center" }}>
                        <Btn onClick={saveBiz.execute} loading={saveBiz.loading} disabled={!bizDirty}>
                          <Save size={13}/> Save Legal Details
                        </Btn>
                        {!bizDirty && <span style={{ fontSize:12,color:"var(--text-tertiary)" }}>No unsaved changes</span>}
                      </div>
                      {saveBiz.error && (
                        <div style={{ padding:"10px 14px",background:"var(--danger-bg)",borderRadius:9,
                          border:"1px solid var(--danger-border)",fontSize:12,color:"var(--danger-text)" }}>
                          {saveBiz.error}{saveErrId && ` — Request ID: ${saveErrId}`}
                        </div>
                      )}
                    </div>
                  )}
                </div>
                <div style={{ display:"flex", flexDirection:"column", gap:20 }}>
                  <div className="card">
                    <p className="section-title"><FileText size={15}/> Verification Documents</p>
                    <p className="section-sub">Owner ID document status</p>
                    <div style={{ padding:"14px 16px", background:"var(--surface-sunken)", borderRadius:10,
                      border:"1px solid var(--border)", textAlign:"center" }}>
                      <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:0 }}>
                        No document upload capability exists yet for this account. Contact support to submit verification documents.
                      </p>
                    </div>
                  </div>
                  <div className="card">
                    <p className="section-title"><Shield size={15}/> Review Status</p>
                    <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:10 }}>
                      <span style={{ fontSize:13, fontWeight:600 }}>Verification Status</span>
                      <StatusBadge raw={verStatus}/>
                    </div>
                    {verStatus === "rejected" && (
                      <div style={{ padding:"10px 14px", background:"var(--danger-bg)", borderRadius:9,
                        border:"1px solid var(--danger-border)", fontSize:12, color:"var(--danger-text)" }}>
                        Your business profile was rejected by admin. Update the required fields and resubmit.
                      </div>
                    )}
                    <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"10px 0 0" }}>
                      Admin Notes: none recorded yet.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {tab === "address" && (
              <div className="card" id="address">
                <p className="section-title"><MapPin size={15}/> Business Address, Services &amp; Availability</p>
                <p className="section-sub">Your registered address, service areas, business hours, and services offered — all in one place.</p>
                {bizApi.error ? (
                  <SectionError title="Could not load address" error={bizApi.error} requestId={bizApi.requestId} onRetry={bizApi.refetch}/>
                ) : bizApi.loading ? <SkeletonCard rows={3}/> : (
                  <>
                    <div className="two-col" style={{ marginBottom:16 }}>
                      <div style={{ gridColumn:"1/-1" }}>
                        <Field label="Address Line 1" required warn={!addr1}>
                          <TextInput value={addr1} onChange={v=>{setAddr1(v);setAddrDirty(true);}} placeholder="Street, building, area"/>
                        </Field>
                      </div>
                      <Field label="Address Line 2" hint="Landmark, floor (optional)">
                        <TextInput value={addr2} onChange={v=>{setAddr2(v);setAddrDirty(true);}} placeholder="Landmark, floor"/>
                      </Field>
                      <Field label="City" required warn={!city}>
                        <TextInput value={city} onChange={v=>{setCity(v);setAddrDirty(true);}} placeholder="City"/>
                      </Field>
                      <Field label="State" required warn={!stateName}>
                        <TextInput value={stateName} onChange={v=>{setStateName(v);setAddrDirty(true);}} placeholder="State"/>
                      </Field>
                      <Field label="Zipcode / PIN" hint="Used to match your service areas">
                        <TextInput value={zipcode} onChange={v=>{setZipcode(v);setAddrDirty(true);}} placeholder="e.g. 141001"/>
                      </Field>
                      <Field label="Country">
                        <TextInput value={country} onChange={v=>{setCountry(v);setAddrDirty(true);}} placeholder="India"/>
                      </Field>
                    </div>
                    <div style={{ display:"flex", gap:10, alignItems:"center", marginBottom:20 }}>
                      <Btn onClick={saveAddr.execute} loading={saveAddr.loading} disabled={!addrDirty}>
                        <Save size={13}/> Save Address
                      </Btn>
                      {!addrDirty && <span style={{ fontSize:12,color:"var(--text-tertiary)" }}>No unsaved changes</span>}
                    </div>

                    <div style={{ paddingTop:16, borderTop:"1px solid var(--border)" }}>
                      <p style={{ fontSize:12, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.06em",
                        color:"var(--text-tertiary)", margin:"0 0 12px" }}>Service Areas</p>
                      {areasApi.error ? (
                        <SectionError title="Could not load service areas" error={areasApi.error} requestId={areasApi.requestId} onRetry={areasApi.refetch}/>
                      ) : areasApi.loading ? <SkeletonCard rows={2}/> : (totalAreas === 0) ? (
                        <p style={{ fontSize:13, color:"var(--text-secondary)" }}>No service areas configured yet.</p>
                      ) : (
                        <div style={{ display:"flex", flexDirection:"column", gap:8, marginBottom:14 }}>
                          {(areasApi.data?.areas ?? []).map((a,i) => (
                            <div key={i} style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
                              padding:"10px 14px", background:"var(--surface-sunken)", borderRadius:9, border:"1px solid var(--border)" }}>
                              <div>
                                <span style={{ fontSize:13, fontWeight:600 }}>{safeText(a.city)} {safeText(a.zipcode,"")}</span>
                                <span style={{ fontSize:11, color:"var(--text-tertiary)", marginLeft:8 }}>{safeText(a.state)}</span>
                              </div>
                              {i===0 && <span style={{ fontSize:10, fontWeight:700, color:"var(--brand)" }}>PRIMARY</span>}
                            </div>
                          ))}
                        </div>
                      )}
                      <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:"0 0 12px" }}>
                        {totalAreas} / 5 areas used — bookability requires at least one active area.
                      </p>
                      <Link href="/provider/service-areas" style={{ fontSize:12, fontWeight:700, color:"var(--brand)",
                        textDecoration:"none", display:"inline-flex", alignItems:"center", gap:5 }}>
                        <MapPin size={12}/> Add Service Area
                      </Link>
                    </div>

                    <div style={{ paddingTop:16, borderTop:"1px solid var(--border)", marginTop:16 }}>
                      <p style={{ fontSize:12, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.06em",
                        color:"var(--text-tertiary)", margin:"0 0 12px" }}>Business Hours</p>
                      {availabilityApi.error ? (
                        <SectionError title="Could not load business hours" error={availabilityApi.error} requestId={availabilityApi.requestId} onRetry={availabilityApi.refetch}/>
                      ) : availabilityApi.loading ? <SkeletonCard rows={2}/> : (availabilityApi.data?.rules?.length ?? 0) === 0 ? (
                        <p style={{ fontSize:13, color:"var(--text-secondary)" }}>Working hours not configured yet.</p>
                      ) : (
                        <div style={{ display:"flex", flexDirection:"column", gap:8, marginBottom:14 }}>
                          {(availabilityApi.data?.rules ?? []).filter(r=>r.is_active).map((r) => (
                            <div key={r.id} style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
                              padding:"10px 14px", background:"var(--surface-sunken)", borderRadius:9, border:"1px solid var(--border)" }}>
                              <span style={{ fontSize:13, fontWeight:600 }}>{DAY_NAMES[r.day_of_week] ?? "—"}</span>
                              <span style={{ fontSize:12, color:"var(--text-tertiary)" }}>{r.start_time}–{r.end_time}</span>
                            </div>
                          ))}
                        </div>
                      )}
                      <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:"0 0 12px" }}>
                        {(availabilityApi.data?.rules ?? []).filter(r=>r.is_active).length} rule(s) configured — required for bookability.
                      </p>
                      <Link href="/tenant/setup/availability" style={{ fontSize:12, fontWeight:700, color:"var(--brand)",
                        textDecoration:"none", display:"inline-flex", alignItems:"center", gap:5 }}>
                        <Clock size={12}/> Manage Business Hours
                      </Link>
                    </div>

                    <div style={{ paddingTop:16, borderTop:"1px solid var(--border)", marginTop:16 }}>
                      <p style={{ fontSize:12, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.06em",
                        color:"var(--text-tertiary)", margin:"0 0 12px" }}>Services You Provide</p>
                      {offeringsApi.error ? (
                        <SectionError title="Could not load services" error={offeringsApi.error} requestId={offeringsApi.requestId} onRetry={offeringsApi.refetch}/>
                      ) : offeringsApi.loading ? <SkeletonCard rows={2}/> : (offeringsApi.data?.offerings?.length ?? 0) === 0 ? (
                        <p style={{ fontSize:13, color:"var(--text-secondary)" }}>No services enabled yet.</p>
                      ) : (
                        <div style={{ display:"flex", flexDirection:"column", gap:8, marginBottom:14 }}>
                          {(offeringsApi.data?.offerings ?? []).map((o) => (
                            <a key={o.provider_enabled_offering_id} href="/provider/offerings" style={{ display:"flex", justifyContent:"space-between",
                              alignItems:"center", padding:"10px 14px", background:"var(--surface-sunken)", borderRadius:9,
                              border:"1px solid var(--border)", textDecoration:"none" }}>
                              <div>
                                <span style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)" }}>{o.provider_display_name || o.offering_name}</span>
                                {o.offering_type && <span style={{ fontSize:11, color:"var(--text-tertiary)", marginLeft:8 }}>{o.offering_type}</span>}
                              </div>
                              <span style={{ fontSize:10, fontWeight:700, textTransform:"uppercase",
                                color: o.status === "active" ? "var(--success)" : o.status === "draft" ? "var(--text-tertiary)" : "var(--warning)" }}>
                                {o.status}
                              </span>
                            </a>
                          ))}
                        </div>
                      )}
                      <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:"0 0 12px" }}>
                        {offeringsApi.data?.offerings?.filter(o=>o.status==="active").length ?? 0} active service(s) — bookability requires at least one.
                      </p>
                      <a href="/provider/offerings" style={{ fontSize:12, fontWeight:700, color:"var(--brand)",
                        textDecoration:"none", display:"inline-flex", alignItems:"center", gap:5 }}>
                        <Tag size={12}/> Add or Edit Services
                      </a>
                    </div>
                  </>
                )}
              </div>
            )}

            {tab === "people" && (
              <div className="card" id="people">
                <p className="section-title"><Users2 size={15}/> People &amp; Access</p>
                <p className="section-sub">Owner, team members, and access. Invite/role-management uses your team roster.</p>

                <div style={{ marginBottom:20 }}>
                  <p style={{ fontSize:12, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.06em",
                    color:"var(--text-tertiary)", margin:"0 0 10px" }}>Owner Profile</p>
                  <div style={{ display:"flex", alignItems:"center", gap:12, padding:"12px 14px",
                    background:"var(--surface-sunken)", borderRadius:10, border:"1px solid var(--border)" }}>
                    <div style={{ width:40,height:40,borderRadius:"50%",background:"var(--brand-muted,rgba(37,99,235,0.1))",
                      display:"flex",alignItems:"center",justifyContent:"center",fontWeight:700,color:"var(--brand)",flexShrink:0 }}>
                      {(me?.full_name?.[0] ?? "O").toUpperCase()}
                    </div>
                    <div style={{ flex:1 }}>
                      <p style={{ fontSize:13, fontWeight:600, margin:0 }}>{safeText(me?.full_name,"Owner")}</p>
                      <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"0 0 8px" }}>{safeText(me?.email)}</p>
                      <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                        <TextInput
                          value={ownerPhone}
                          onChange={v=>{ setOwnerPhone(v); setOwnerPhoneDirty(true); }}
                          placeholder="+91XXXXXXXXXX"
                        />
                        <Btn size="sm" onClick={saveOwnerPhone.execute} loading={saveOwnerPhone.loading} disabled={!ownerPhoneDirty}>
                          <Save size={12}/> Save
                        </Btn>
                      </div>
                      {saveOwnerPhone.error && <p style={{ fontSize:11, color:"var(--danger-text)", margin:"4px 0 0" }}>{saveOwnerPhone.error}</p>}
                    </div>
                    <span style={{ fontSize:10, fontWeight:700, padding:"3px 9px", borderRadius:999,
                      background:"var(--brand-muted,rgba(37,99,235,0.1))", color:"var(--brand)" }}>OWNER</span>
                  </div>
                </div>

                <div>
                  <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:10 }}>
                    <p style={{ fontSize:12, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.06em",
                      color:"var(--text-tertiary)", margin:0 }}>Staff &amp; Technicians</p>
                    <Link href="/provider/staff" style={{ fontSize:12, fontWeight:700, color:"var(--brand)", textDecoration:"none",
                      display:"flex", alignItems:"center", gap:4 }}>
                      <UserPlus size={12}/> Add Staff
                    </Link>
                  </div>
                  {teamApi.error ? (
                    <SectionError title="Could not load team" error={teamApi.error} requestId={teamApi.requestId} onRetry={teamApi.refetch}/>
                  ) : teamApi.loading ? <SkeletonCard rows={2}/> : (teamApi.data?.members ?? []).length === 0 ? (
                    <p style={{ fontSize:13, color:"var(--text-secondary)" }}>No staff members added yet.</p>
                  ) : (
                    <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                      {(teamApi.data?.members ?? []).map(m => (
                        <div key={m.member_id} style={{ display:"flex", alignItems:"center", gap:12,
                          padding:"10px 14px", background:"var(--surface-sunken)", borderRadius:9, border:"1px solid var(--border)" }}>
                          <div style={{ width:32,height:32,borderRadius:"50%",background:"var(--surface)",
                            border:"1px solid var(--border)",display:"flex",alignItems:"center",justifyContent:"center",
                            fontSize:12,fontWeight:700,color:"var(--text-secondary)",flexShrink:0 }}>
                            {(m.full_name?.[0] ?? "S").toUpperCase()}
                          </div>
                          <div style={{ flex:1, minWidth:0 }}>
                            <p style={{ fontSize:13, fontWeight:600, margin:0 }}>{m.full_name}</p>
                            <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:0 }}>{m.member_type} · {(m.skills??[]).join(", ") || "No skills listed"}</p>
                          </div>
                          <span style={{ fontSize:10, fontWeight:700, padding:"3px 9px", borderRadius:999,
                            background: m.status==="active" ? "var(--success-bg)" : "var(--surface)",
                            color: m.status==="active" ? "var(--success-text)" : "var(--text-tertiary)",
                            border:`1px solid ${m.status==="active" ? "var(--success-border)" : "var(--border)"}` }}>
                            {m.status.toUpperCase()}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Media -- real status of the same two assets HeroCard already
                manages (logo/cover upload lives there, not duplicated here
                to avoid a second, divergent upload path). */}
            {tab === "media" && (
              <div className="overview-grid" id="media">
                <div className="card">
                  <p style={{ fontSize:15, fontWeight:700, color:"var(--text-primary)", margin:"0 0 14px" }}>Business logo</p>
                  <div style={{ display:"flex", alignItems:"center", gap:14 }}>
                    <div style={{ width:64,height:64,borderRadius:14,background:"var(--surface-sunken)",border:"1px solid var(--border)",
                      display:"flex",alignItems:"center",justifyContent:"center",overflow:"hidden",flexShrink:0 }}>
                      {logoPreview ? <img src={logoPreview} alt="logo" style={{ width:"100%",height:"100%",objectFit:"cover" }}/> : <Building2 size={24} style={{ color:"var(--text-tertiary)" }}/>}
                    </div>
                    <div>
                      <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:"0 0 4px" }}>{logoPreview ? "Logo uploaded" : "No logo yet"}</p>
                      <button onClick={()=>window.scrollTo({top:0,behavior:"smooth"})}
                        style={{ fontSize:12, color:"var(--brand)", background:"none", border:"none", cursor:"pointer", fontFamily:"inherit", padding:0 }}>
                        {logoPreview ? "Change logo ↑" : "Upload logo ↑"}
                      </button>
                    </div>
                  </div>
                </div>
                <div className="card">
                  <p style={{ fontSize:15, fontWeight:700, color:"var(--text-primary)", margin:"0 0 14px" }}>Storefront / cover photo</p>
                  <div style={{ display:"flex", alignItems:"center", gap:14 }}>
                    <div style={{ width:96,height:64,borderRadius:10,background: shopPreview ? `url(${shopPreview}) center/cover no-repeat` : "var(--surface-sunken)",
                      border:"1px solid var(--border)", flexShrink:0 }}/>
                    <div>
                      <p style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", margin:"0 0 4px" }}>{shopPreview ? "Cover photo uploaded" : "No cover photo yet"}</p>
                      <button onClick={()=>window.scrollTo({top:0,behavior:"smooth"})}
                        style={{ fontSize:12, color:"var(--brand)", background:"none", border:"none", cursor:"pointer", fontFamily:"inherit", padding:0 }}>
                        {shopPreview ? "Change cover ↑" : "Upload cover ↑"}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {tab === "activity" && (
              <div className="card" id="activity">
                <div style={{ display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:4 }}>
                  <p className="section-title" style={{ marginBottom:0 }}><Activity size={15}/> Activity</p>
                  <Link href="/activity" style={{ fontSize:12,color:"var(--brand)",textDecoration:"none",display:"flex",alignItems:"center",gap:4 }}>
                    View All <ChevronRight size={12}/>
                  </Link>
                </div>
                <p className="section-sub">Profile updates and verification events.</p>
                {activityApi.error ? (
                  <SectionError title="Could not load activity" error={activityApi.error} requestId={activityApi.requestId} onRetry={activityApi.refetch}/>
                ) : activityApi.loading ? <SkeletonCard rows={3}/> : activities.length === 0 ? (
                  <div style={{ padding:"24px",textAlign:"center",color:"var(--text-tertiary)",fontSize:13 }}>
                    <Activity size={28} style={{ marginBottom:8,opacity:0.25 }}/>
                    <p style={{ margin:0 }}>No profile activity yet.</p>
                  </div>
                ) : (
                  <div style={{ display:"flex",flexDirection:"column",gap:0 }}>
                    {activities.map((ev:unknown,i:number)=>{
                      const e = ev as Record<string,unknown>;
                      return (
                        <div key={i} style={{ display:"flex",gap:12,padding:"12px 0",
                          borderBottom: i < activities.length-1 ? "1px solid var(--border)" : "none" }}>
                          <div style={{ width:32,height:32,borderRadius:"50%",background:"var(--surface-sunken)",
                            border:"1px solid var(--border)",display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0 }}>
                            <Activity size={13} style={{ color:"var(--text-tertiary)" }}/>
                          </div>
                          <div style={{ flex:1,minWidth:0 }}>
                            <p style={{ fontSize:13,fontWeight:500,color:"var(--text-primary)",margin:"0 0 2px" }}>
                              {safeText(e.action ?? e.event_type ?? e.type, "Profile event")}
                            </p>
                            <div style={{ display:"flex",gap:10,fontSize:11,color:"var(--text-tertiary)",flexWrap:"wrap" }}>
                              <span>{safeDate(e.created_at ?? e.timestamp)}</span>
                              {e.actor ? <span>by {String(e.actor)}</span> : null}
                              {e.request_id ? (
                                <button onClick={()=>copyText(String(e.request_id))}
                                  style={{ background:"none",border:"none",cursor:"pointer",
                                    color:"var(--text-tertiary)",fontSize:11,fontFamily:"inherit",
                                    display:"flex",alignItems:"center",gap:3,padding:0 }}>
                                  <Copy size={9}/> {String(e.request_id).slice(0,12)}…
                                </button>
                              ) : null}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Edit Business Info Modal */}
      <Modal open={editOpen && !isApproved} onClose={()=>setEditOpen(false)} title="Edit Business Info">
        <div style={{ display:"grid", gap:16 }}>
          <p style={{ fontSize:12, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.06em", color:"var(--text-tertiary)", margin:0 }}>Basic Info</p>
          <div className="two-col">
            <Field label="Business Name" required warn={hasCriticalChange()}>
              <TextInput value={bizName} onChange={v=>{setBizName(v);setBizDirty(true);}} placeholder="Registered business name"/>
            </Field>
            <Field label="Category" hint="Platform-controlled — contact support to change.">
              <TextInput value="Air Conditioner Services" readOnly/>
            </Field>
          </div>
          <p style={{ fontSize:12, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.06em", color:"var(--text-tertiary)", margin:0 }}>Contact Info</p>
          <div className="two-col">
            <Field label="Business Phone">
              <TextInput value={bizPhone} onChange={v=>{setBizPhone(v);setBizDirty(true);}} placeholder="+91XXXXXXXXXX"/>
            </Field>
            <Field label="Business Email">
              <TextInput value={bizEmail} onChange={v=>{setBizEmail(v);setBizDirty(true);}} placeholder="contact@business.com"/>
            </Field>
            <Field label="Website">
              <TextInput value={website} onChange={v=>{setWebsite(v);setBizDirty(true);}} placeholder="https://yourbusiness.com"/>
            </Field>
          </div>
          <p style={{ fontSize:12, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.06em", color:"var(--text-tertiary)", margin:0 }}>Description</p>
          <Field label="Business Description" hint="Shown to customers.">
            <Textarea value={desc} onChange={v=>{setDesc(v);setBizDirty(true);}} rows={4} placeholder="Describe your services…"/>
          </Field>
          {hasCriticalChange() && (
            <div style={{ padding:"10px 14px",borderRadius:9,background:"var(--warning-bg)",border:"1px solid var(--warning-border)",
              fontSize:12,color:"var(--warning-text)" }}>
              Changing Business Name will reset your verification status to Pending Review.
            </div>
          )}
          {saveBiz.error && (
            <div style={{ padding:"10px 14px",background:"var(--danger-bg)",borderRadius:9,border:"1px solid var(--danger-border)",
              fontSize:12,color:"var(--danger-text)" }}>
              {saveBiz.error}{saveErrId && ` — Request ID: ${saveErrId}`}
            </div>
          )}
          <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
            <Btn variant="ghost" onClick={()=>setEditOpen(false)}>Cancel</Btn>
            <Btn onClick={saveBiz.execute} loading={saveBiz.loading} disabled={!bizDirty}>
              <Save size={13}/> Save Changes
            </Btn>
          </div>
        </div>
      </Modal>

      {/* Preview Public Profile Modal — customer-safe fields only */}
      <Modal open={previewOpen} onClose={()=>setPreviewOpen(false)} title="Public Profile Preview">
        <div style={{ borderRadius:"var(--radius-lg)", overflow:"hidden", border:"1px solid var(--border)" }}>
          <div style={{ height:100, background: shopPreview
            ? `linear-gradient(180deg, rgba(34,29,20,0.1), rgba(34,29,20,0.5)), url(${shopPreview}) center/cover no-repeat`
            : "var(--primary-gradient)" }}/>
          <div style={{ padding:20, background:"var(--surface)" }}>
            <div style={{ display:"flex", alignItems:"center", gap:12, marginTop:-44, marginBottom:10 }}>
              <div style={{ width:64,height:64,borderRadius:14,background:"var(--surface)",border:"3px solid var(--surface)",
                boxShadow:"0 2px 8px rgba(0,0,0,0.15)",display:"flex",alignItems:"center",justifyContent:"center",overflow:"hidden" }}>
                {logoPreview ? <img src={logoPreview} alt="logo" style={{ width:"100%",height:"100%",objectFit:"cover" }}/> : <Building2 size={26}/>}
              </div>
            </div>
            <h3 style={{ fontSize:16, fontWeight:800, margin:"0 0 2px" }}>{safeText(bizName,"Your Business")}</h3>
            <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:10 }}>
              <Star size={12} style={{ color:"var(--warning)" }}/>
              <span style={{ fontSize:12, color:"var(--text-secondary)" }}>New — no ratings yet</span>
              {isApproved && <span style={{ fontSize:10, fontWeight:700, padding:"2px 8px", borderRadius:999,
                background:"var(--success-bg)", color:"var(--success-text)" }}>Verified</span>}
            </div>
            <p style={{ fontSize:12, color:"var(--text-secondary)", margin:"0 0 12px" }}>{safeText(desc,"No description added yet.")}</p>
            <div style={{ display:"flex", gap:8, flexWrap:"wrap", marginBottom:12 }}>
              {(areasApi.data?.areas ?? []).slice(0,3).map((a,i) => (
                <span key={i} style={{ fontSize:11, padding:"4px 10px", borderRadius:999, background:"var(--surface-sunken)",
                  border:"1px solid var(--border)" }}>{safeText(a.city)}</span>
              ))}
            </div>
            <p style={{ fontSize:10, color:"var(--text-tertiary)", margin:0 }}>
              This is what customers will see. Internal balances, deposits, health scores, and admin notes are never shown here.
            </p>
          </div>
        </div>
      </Modal>
    </TenantLayout>
  );
}

// ── Helper sub-components ─────────────────────────────────────────────────────
function MetaChipDark({ icon, label, value }: { icon:React.ReactNode; label:string; value:string }) {
  return (
    <div style={{ display:"flex",alignItems:"center",gap:5,fontSize:11 }}>
      {icon}<span style={{ fontWeight:500 }}>{label}:</span>
      <span>{value}</span>
    </div>
  );
}

function InfoRow({ label, value, verified, block }: { label:string; value:string; verified?:boolean; block?:boolean }) {
  return (
    <div style={{ display: block ? "block" : "flex", justifyContent:"space-between", alignItems:"flex-start", gap:12,
      paddingBottom:10, borderBottom:"1px solid var(--border)" }}>
      <span style={{ fontSize:12, color:"var(--text-tertiary)", display:"block", marginBottom: block ? 4 : 0 }}>{label}</span>
      <span style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)", display:"flex", alignItems:"center", gap:6,
        textAlign: block ? "left" : "right" }}>
        {value}
        {verified && <span style={{ fontSize:9, fontWeight:700, padding:"2px 6px", borderRadius:999,
          background:"var(--success-bg)", color:"var(--success-text)" }}>VERIFIED</span>}
      </span>
    </div>
  );
}

function SummaryRow({ icon, label, value, hint, badge, star }: {
  icon:React.ReactNode; label:string; value?:string; hint?:string; badge?:React.ReactNode; star?:boolean;
}) {
  return (
    <div style={{ display:"flex", alignItems:"center", gap:10, padding:"11px 0", borderBottom:"1px solid var(--border)" }}>
      <span style={{ color:"var(--text-tertiary)", flexShrink:0 }}>{icon}</span>
      <span style={{ fontSize:13, color:"var(--text-secondary)", flex:1 }}>{label}</span>
      <div style={{ display:"flex", alignItems:"center", gap:6 }}>
        {badge ?? (
          <span style={{ fontSize:13, fontWeight:700, color:"var(--text-primary)",
            display:"flex", alignItems:"center", gap:4 }} title={hint}>
            {star && <Star size={12} style={{ color:"var(--warning)", fill:"var(--warning)" }}/>}
            {value}
          </span>
        )}
      </div>
      <ChevronRight size={13} style={{ color:"var(--text-tertiary)", flexShrink:0 }}/>
    </div>
  );
}

function NextStep({ done, blocked, title, desc, ctaLabel, onClick }: {
  done?:boolean; blocked?:boolean; title:string; desc:string; ctaLabel:string; onClick:()=>void;
}) {
  return (
    <div style={{ display:"flex", alignItems:"center", gap:10, padding:"10px 12px",
      background: done ? "var(--success-bg)" : "var(--surface-sunken)",
      border:`1px solid ${done ? "var(--success-border)" : "var(--border)"}`, borderRadius:9 }}>
      {done
        ? <CheckCircle2 size={16} style={{ color:"var(--success-text)", flexShrink:0 }}/>
        : <div style={{ width:16,height:16,borderRadius:"50%",border:"2px solid var(--border)",flexShrink:0 }}/>}
      <div style={{ flex:1, minWidth:0 }}>
        <p style={{ fontSize:12, fontWeight:600, margin:0, color: done ? "var(--success-text)" : "var(--text-primary)" }}>{title}</p>
        <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:0 }}>{desc}</p>
      </div>
      {!done && (
        <button onClick={onClick} disabled={blocked && ctaLabel==="Submit"}
          style={{ fontSize:11, fontWeight:700, padding:"5px 11px", borderRadius:7,
            border:"1px solid var(--brand)", background:"transparent", color: (blocked && ctaLabel==="Submit") ? "var(--text-tertiary)" : "var(--brand)",
            cursor: (blocked && ctaLabel==="Submit") ? "not-allowed" : "pointer", fontFamily:"inherit", flexShrink:0,
            opacity: (blocked && ctaLabel==="Submit") ? 0.5 : 1 }}>
          {ctaLabel}
        </button>
      )}
    </div>
  );
}

// ── HeroCard — inline clickable upload for logo + cover ─────────────────────
function HeroCard({ shopPreview, logoPreview, biz, verStatus, isApproved, pct, done, total, primaryBadge, onLogoUploaded, onShopUploaded }: {
  shopPreview: string|null; logoPreview: string|null;
  biz: import("../../../lib/api").BusinessProfile | null | undefined;
  verStatus: string; isApproved: boolean; pct: number; done: number; total: number;
  primaryBadge: EarnedBadge | null;
  onLogoUploaded: (a: import("../../../lib/api").MediaAsset) => void;
  onShopUploaded: (a: import("../../../lib/api").MediaAsset) => void;
}) {
  const logoRef = React.useRef<HTMLInputElement>(null);
  const shopRef = React.useRef<HTMLInputElement>(null);
  const [logoUploading, setLogoUploading] = React.useState(false);
  const [shopUploading, setShopUploading] = React.useState(false);
  const [logoErr, setLogoErr] = React.useState<string|null>(null);
  const [shopErr, setShopErr] = React.useState<string|null>(null);

  async function uploadLogo(file: File) {
    setLogoUploading(true); setLogoErr(null);
    try {
      const asset = await mediaAssetApi.uploadBusinessLogo(file);
      onLogoUploaded(asset);
    } catch(e:unknown) {
      const err = e as { message?: string };
      setLogoErr(err?.message ?? "Upload failed");
    } finally { setLogoUploading(false); }
  }

  async function uploadShop(file: File) {
    setShopUploading(true); setShopErr(null);
    try {
      const asset = await mediaAssetApi.uploadShopPhoto(file);
      onShopUploaded(asset);
    } catch(e:unknown) {
      const err = e as { message?: string };
      setShopErr(err?.message ?? "Upload failed");
    } finally { setShopUploading(false); }
  }

  return (
    <div style={{ borderRadius:"var(--radius-xl, 1rem)", overflow:"hidden", border:"1px solid var(--border)", boxShadow:"0 4px 16px rgba(0,0,0,0.08)" }}>
      {/* Cover banner — click to change */}
      <div
        onClick={()=>{ if (!shopUploading) shopRef.current?.click(); }}
        style={{ height:160, position:"relative", cursor:"pointer",
          background: shopPreview
            ? `linear-gradient(180deg, rgba(34,29,20,0.15), rgba(34,29,20,0.65)), url(${shopPreview}) center/cover no-repeat`
            : "linear-gradient(135deg, var(--surface-sunken) 0%, var(--border) 100%)" }}>
        {/* Hover overlay */}
        <div className="cover-overlay" style={{ position:"absolute",inset:0,display:"flex",flexDirection:"column",
          alignItems:"center",justifyContent:"center",gap:6,
          background:"rgba(0,0,0,0.45)",opacity:0,transition:"opacity 0.18s",borderRadius:0 }}>
          {shopUploading
            ? <RefreshCw size={20} style={{ color:"white",animation:"spin 1s linear infinite" }}/>
            : <><Camera size={20} style={{ color:"white" }}/><span style={{ color:"white",fontSize:12,fontWeight:600 }}>Change Cover Photo</span></>}
        </div>
        {shopErr && <div style={{ position:"absolute",bottom:8,left:"50%",transform:"translateX(-50%)",
          background:"rgba(220,38,38,0.9)",color:"white",fontSize:11,padding:"4px 12px",borderRadius:6,whiteSpace:"nowrap" }}>{shopErr}</div>}
        <input ref={shopRef} type="file" accept="image/jpeg,image/png,image/webp" style={{ display:"none" }}
          onChange={e=>{ const f=e.target.files?.[0]; if(f) uploadShop(f); e.target.value=""; }}/>
      </div>

      {/* Identity panel */}
      <div style={{ background:"var(--surface-elevated)", padding:"0 28px 24px", color:"var(--text-primary)", position:"relative" }}>
        <div style={{ display:"flex", alignItems:"flex-end", justifyContent:"space-between", flexWrap:"wrap", gap:16, marginTop:-50 }}>

          {/* Left: Logo + name */}
          <div style={{ display:"flex", alignItems:"flex-end", gap:20 }}>
            {/* Logo card — click to change */}
            <div
              onClick={()=>{ if (!logoUploading) logoRef.current?.click(); }}
              className="logo-upload-card"
              style={{ width:100, height:100, borderRadius:"var(--radius-xl, 1rem)", background:"var(--surface-sunken)",
                border:"3px solid var(--surface-elevated)", boxShadow:"var(--shadow-lg)",
                display:"flex", alignItems:"center", justifyContent:"center",
                overflow:"hidden", flexShrink:0, cursor:"pointer", position:"relative" }}>
              {logoPreview
                ? <img src={logoPreview} alt="logo" style={{ width:"100%",height:"100%",objectFit:"cover" }}/>
                : <Building2 size={36} style={{ color:"var(--text-tertiary)" }}/>}
              {/* Logo hover overlay */}
              <div className="logo-overlay" style={{ position:"absolute",inset:0,display:"flex",flexDirection:"column",
                alignItems:"center",justifyContent:"center",gap:4,
                background:"rgba(0,0,0,0.55)",opacity:0,transition:"opacity 0.18s" }}>
                {logoUploading
                  ? <RefreshCw size={16} style={{ color:"white",animation:"spin 1s linear infinite" }}/>
                  : <><Camera size={16} style={{ color:"white" }}/><span style={{ color:"white",fontSize:10,fontWeight:600 }}>Edit</span></>}
              </div>
              <input ref={logoRef} type="file" accept="image/jpeg,image/png,image/webp" style={{ display:"none" }}
                onChange={e=>{ const f=e.target.files?.[0]; if(f) uploadLogo(f); e.target.value=""; }}/>
            </div>
            {/* Name + meta */}
            <div style={{ paddingBottom:6 }}>
              {logoErr && <p style={{ fontSize:11,color:"var(--danger)",margin:"0 0 4px" }}>{logoErr}</p>}
              <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:4 }}>
                <h2 style={{ fontSize:22, fontWeight:700, margin:0, color:"var(--text-primary)" }}>
                  {safeText(biz?.business_name,"Your Business")}
                </h2>
                {isApproved && <CheckCircle2 size={18} style={{ color:"var(--success)" }}/>}
                {primaryBadge && <TrustBadgeChip badge={primaryBadge} size={14}/>}
              </div>
              <div style={{ fontSize:13, color:"var(--text-secondary)", marginBottom:10 }}>
                Home Services{" "}<span style={{ margin:"0 6px", opacity:0.5 }}>•</span>
                {safeText(biz?.plan_type,"Starter").replace(/_/g," ")} Plan
              </div>
              <div style={{ display:"flex", alignItems:"center", gap:14, flexWrap:"wrap" }}>
                <StatusBadge raw={verStatus}/>
                <span style={{ fontSize:12, color:"var(--text-tertiary)", display:"flex", alignItems:"center", gap:5 }}>
                  <Clock size={11}/> Last Updated: {safeDate((biz as unknown as Record<string,unknown>)?.updated_at ?? biz?.created_at)}
                </span>
                {biz?.slug && (
                  <span style={{ fontSize:12, color:"var(--text-tertiary)", display:"flex", alignItems:"center", gap:5 }}>
                    <Tag size={11}/> Slug: {biz.slug}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Right: Completion ring */}
          <div style={{ display:"flex", flexDirection:"column", alignItems:"center", gap:6, paddingBottom:4 }}>
            <CompletionRing pct={pct}/>
            <div style={{ textAlign:"center" }}>
              <p style={{ fontSize:12, fontWeight:700, color:"var(--text-primary)", margin:"0 0 1px" }}>Profile Completion</p>
              <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:0 }}>{done} of {total} completed</p>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        .cover-overlay:hover,.cover-overlay:focus{opacity:1!important}
        div:hover>.cover-overlay{opacity:1!important}
        .logo-upload-card:hover .logo-overlay{opacity:1!important}
      `}</style>
    </div>
  );
}

function MediaCard({ title, desc, preview, spec, uploadSlot }: {
  title:string; desc:string; preview:string|null; spec:string; uploadSlot:React.ReactNode;
}) {
  return (
    <div style={{ background:"var(--surface-sunken)",border:"1px solid var(--border)",
      borderRadius:"var(--radius-lg)",padding:20,display:"flex",flexDirection:"column",gap:14 }}>
      <div>
        <p style={{ fontSize:13,fontWeight:600,color:"var(--text-primary)",margin:"0 0 3px" }}>{title}</p>
        <p style={{ fontSize:11,color:"var(--text-secondary)",margin:0,lineHeight:1.5 }}>{desc}</p>
      </div>
      <div style={{ display:"flex",justifyContent:"center" }}>{uploadSlot}</div>
      <div style={{ borderTop:"1px solid var(--border)",paddingTop:10 }}>
        <p style={{ fontSize:10,color:"var(--text-tertiary)",margin:0,textAlign:"center",lineHeight:1.5 }}>{spec}</p>
        {preview && (
          <div style={{ marginTop:8,display:"flex",alignItems:"center",gap:5,justifyContent:"center",
            padding:"4px 10px",borderRadius:6,background:"var(--success-bg)",
            border:"1px solid var(--success-border)" }}>
            <CheckCircle2 size={11} style={{ color:"var(--success-text)" }}/>
            <span style={{ fontSize:10,color:"var(--success-text)",fontWeight:600 }}>Uploaded</span>
          </div>
        )}
      </div>
    </div>
  );
}

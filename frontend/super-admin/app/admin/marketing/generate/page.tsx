"use client";
/**
 * Generate & Schedule Post Wizard — 8 steps: Goal, Target, Channel, Creative
 * Brief, AI Generation, Preview & Edit, Approval, Schedule.
 * PROVEN: every AI action calls marketingCommandCenterApi.generate* (real
 * platform-AI-budget-charged endpoints) — no client-side fake content.
 */
import React, { useState, useCallback } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Btn, Input, Select, Badge, SectionHeader } from "../../../../components/shared/ui";
import { Sparkles, ImageIcon, Hash, Wand2, CheckCircle2 } from "lucide-react";
import { marketingCommandCenterApi } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";

const STEPS = ["Goal", "Target", "Channel", "Creative Brief", "AI Generation", "Preview & Edit", "Approval", "Schedule"];

const GOALS = ["brand_awareness","lead_generation","booking_conversion","festival_promotion",
  "service_education","offer_announcement","provider_spotlight","customer_trust"];
const POST_TYPES = ["image_post","carousel","story","reel_script","short_video_script","text_post","offer_post","service_highlight"];
const LANGUAGES = ["english","hindi","punjabi"];
const TONES = ["professional","friendly","premium","local_punjabi","festival","urgent","educational"];
const VERTICALS = ["home_services","coaching_ielts","real_estate","restaurant_food","product_marketplace","professional_services","beauty_wellness"];
const CTAS = ["Book Now","Call Now","Send Enquiry","Get Free Demo","Schedule Site Visit","Order Now"];
const CHANNELS_ALL = ["facebook","instagram","google_business","linkedin","youtube","whatsapp"];

function opt(vals: string[]) { return vals.map(v => ({ value: v, label: v.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()) })); }

export default function GenerateSchedulePostWizard() {
  const [step, setStep] = useState(0);
  const [postId, setPostId] = useState<string | null>(null);

  // Step 1 — Goal
  const [goal, setGoal] = useState("offer_announcement");
  const [postType, setPostType] = useState("image_post");
  const [language, setLanguage] = useState("english");
  const [tone, setTone] = useState("friendly");

  // Step 2 — Target
  const [vertical, setVertical] = useState("home_services");
  const [city, setCity] = useState("");
  const [audience, setAudience] = useState("Homeowners");

  // Step 3 — Channel
  const accounts = useApi(useCallback(() => marketingCommandCenterApi.listSocialAccounts(), []));
  const [channels, setChannels] = useState<string[]>([]);
  const connectedPlatforms = new Set((accounts.data?.items ?? []).filter(a => a.status === "active").map(a => a.platform));

  // Step 4 — Creative brief
  const [mainMessage, setMainMessage] = useState("");
  const [cta, setCta] = useState("Book Now");
  const [hashtagsInput, setHashtagsInput] = useState("");

  // Step 5 — AI generation
  const [caption, setCaption] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [hashtags, setHashtags] = useState<string[]>([]);
  const [estimatedCost, setEstimatedCost] = useState(0);

  const captionAction = useAction(useCallback((data: Record<string, unknown>) => marketingCommandCenterApi.generateCaption(data), []));
  const imageAction   = useAction(useCallback((data: Record<string, unknown>) => marketingCommandCenterApi.generateImage(data), []));
  const hashtagAction = useAction(useCallback((data: Record<string, unknown>) => marketingCommandCenterApi.generateHashtags(data), []));
  const createAction  = useAction(useCallback((data: Record<string, unknown>) => marketingCommandCenterApi.createPost(data), []));
  const submitApprovalAction = useAction(useCallback((id: string) => marketingCommandCenterApi.submitApproval(id), []));
  const approveAction = useAction(useCallback((id: string) => marketingCommandCenterApi.approvePost(id), []));
  const scheduleAction = useAction(useCallback((id: string, at: string, ch: string[]) => marketingCommandCenterApi.schedulePost(id, at, ch), []));

  // Step 7 — Approval
  const [approvalChoice, setApprovalChoice] = useState<"draft"|"submit"|"approve_now">("submit");

  // Step 8 — Schedule
  const [scheduleDate, setScheduleDate] = useState("");
  const [scheduleTime, setScheduleTime] = useState("10:00");
  const [scheduleError, setScheduleError] = useState<string | null>(null);

  async function ensurePost(): Promise<string> {
    if (postId) return postId;
    const res = await createAction.execute({
      title: mainMessage.slice(0, 80) || "Untitled Post", post_type: postType, vertical_key: vertical,
      goal, language, tone, cta, target_locations: city ? [city] : [],
    });
    if (res) { setPostId(res.id); return res.id; }
    throw new Error("Could not create post draft.");
  }

  async function handleGenerateCaption() {
    const id = await ensurePost();
    const res = await captionAction.execute({ post_id: id, main_message: mainMessage, goal, tone });
    if (res) { setCaption(res.caption); setEstimatedCost(c => c + res.estimated_cost); }
  }
  async function handleGenerateImage() {
    const id = await ensurePost();
    const res = await imageAction.execute({ post_id: id, prompt: mainMessage || goal });
    if (res) { setImageUrl(res.image_url); setEstimatedCost(c => c + res.estimated_cost); }
  }
  async function handleGenerateHashtags() {
    const id = await ensurePost();
    const res = await hashtagAction.execute({ post_id: id, vertical });
    if (res) { setHashtags(res.hashtags); setEstimatedCost(c => c + res.estimated_cost); }
  }

  async function handleApprovalStep() {
    const id = await ensurePost();
    await marketingCommandCenterApi.updatePost(id, { caption, hashtags, cta, channels: [] });
    if (approvalChoice === "submit") await submitApprovalAction.execute(id);
    if (approvalChoice === "approve_now") await approveAction.execute(id);
    setStep(7);
  }

  async function handleSchedule() {
    setScheduleError(null);
    if (!scheduleDate) { setScheduleError("Please choose a date."); return; }
    const scheduledAt = new Date(`${scheduleDate}T${scheduleTime}:00`);
    if (scheduledAt.getTime() <= Date.now()) { setScheduleError("Cannot schedule a post in the past."); return; }
    if (channels.length === 0) { setScheduleError("Select at least one connected channel in Step 3."); return; }
    const id = await ensurePost();
    const res = await scheduleAction.execute(id, scheduledAt.toISOString(), channels);
    if (res) { window.location.href = "/admin/marketing"; }
    else if (scheduleAction.error) setScheduleError(scheduleAction.error);
  }

  const canNext = step < STEPS.length - 1;
  const canPrev = step > 0;

  return (
    <AdminLayout activeNav="marketing">
      <SectionHeader title="Generate & Schedule Post"
        subtitle="8-step guided workflow — preview and approval required before anything publishes."
        icon={<Sparkles size={20}/>}/>

      {/* Step indicator */}
      <div style={{ display:"flex", gap:6, marginBottom:24, flexWrap:"wrap" }}>
        {STEPS.map((label, i) => (
          <div key={label} onClick={() => i < step && setStep(i)} style={{
            fontSize:12, fontWeight:600, padding:"6px 12px", borderRadius:8,
            cursor: i < step ? "pointer" : "default",
            background: i === step ? "var(--accent)" : i < step ? "var(--success-bg)" : "var(--surface-sunken)",
            color: i === step ? "var(--text-on-brand)" : i < step ? "var(--success-text)" : "var(--text-tertiary)",
            border: `1px solid ${i === step ? "var(--accent)" : "var(--border)"}`,
          }}>{i+1}. {label}</div>
        ))}
      </div>

      <Card padding={24} style={{ maxWidth: 720 }}>
        {/* Step 1 — Goal */}
        {step === 0 && (
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <Select label="Marketing Goal *" value={goal} onChange={setGoal} options={opt(GOALS)}/>
            <Select label="Post Type *" value={postType} onChange={setPostType} options={opt(POST_TYPES)}/>
            <Select label="Language *" value={language} onChange={setLanguage} options={opt(LANGUAGES)}/>
            <Select label="Tone *" value={tone} onChange={setTone} options={opt(TONES)}/>
          </div>
        )}

        {/* Step 2 — Target */}
        {step === 1 && (
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <Select label="Vertical *" value={vertical} onChange={setVertical} options={opt(VERTICALS)}/>
            <Input label="City / Region" placeholder="e.g. Ludhiana" value={city} onChange={setCity}/>
            <Select label="Audience" value={audience} onChange={setAudience} options={opt([
              "Homeowners","Students","Property buyers","Food customers","Small businesses","Parents","Working professionals",
            ])}/>
          </div>
        )}

        {/* Step 3 — Channel */}
        {step === 2 && (
          <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
            <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>Only connected channels can be selected.</p>
            {CHANNELS_ALL.map(c => {
              const connected = connectedPlatforms.has(c);
              const checked = channels.includes(c);
              return (
                <label key={c} style={{
                  display:"flex", alignItems:"center", gap:10, padding:"10px 14px", borderRadius:8,
                  border: checked ? "1px solid var(--accent)" : "1px solid var(--border)",
                  background: connected ? "var(--surface-sunken)" : "var(--surface)",
                  opacity: connected ? 1 : 0.5, cursor: connected ? "pointer" : "not-allowed",
                }}>
                  <input type="checkbox" checked={checked} disabled={!connected}
                    onChange={e => setChannels(prev => e.target.checked ? [...prev, c] : prev.filter(x => x !== c))}/>
                  <span style={{ fontSize:13, color:"var(--text-primary)", textTransform:"capitalize" }}>{c.replace("_"," ")}</span>
                  {!connected && <Badge variant="warning" size="sm">Not connected</Badge>}
                </label>
              );
            })}
          </div>
        )}

        {/* Step 4 — Creative Brief */}
        {step === 3 && (
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <Input label="Main Message *" placeholder="Beat the heat with 20% off AC repair"
              value={mainMessage} onChange={setMainMessage}/>
            <Select label="CTA *" value={cta} onChange={setCta} options={opt(CTAS.map(c => c.replace(/ /g,"_")))}/>
            <Input label="Hashtags (comma separated, optional)" placeholder="#ACRepair, #SummerOffer"
              value={hashtagsInput} onChange={setHashtagsInput}/>
          </div>
        )}

        {/* Step 5 — AI Generation */}
        {step === 4 && (
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <div style={{ display:"flex", gap:10, flexWrap:"wrap" }}>
              <Btn variant="primary" size="sm" icon={<Wand2 size={14}/>} loading={captionAction.loading} onClick={handleGenerateCaption}>Generate Caption</Btn>
              <Btn variant="secondary" size="sm" icon={<ImageIcon size={14}/>} loading={imageAction.loading} onClick={handleGenerateImage}>Generate Image</Btn>
              <Btn variant="secondary" size="sm" icon={<Hash size={14}/>} loading={hashtagAction.loading} onClick={handleGenerateHashtags}>Generate Hashtags</Btn>
            </div>
            {(captionAction.error || imageAction.error || hashtagAction.error) && (
              <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>
                {captionAction.error || imageAction.error || hashtagAction.error}
              </p>
            )}
            {caption && <div style={{ padding:12, borderRadius:8, background:"var(--surface-sunken)" }}>
              <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"0 0 4px" }}>Caption</p>
              <p style={{ fontSize:13, color:"var(--text-primary)", margin:0, whiteSpace:"pre-wrap" }}>{caption}</p>
            </div>}
            {imageUrl && <div style={{ padding:12, borderRadius:8, background:"var(--surface-sunken)" }}>
              <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"0 0 4px" }}>Generated Image</p>
              <p style={{ fontSize:12, color:"var(--text-secondary)", fontFamily:"monospace", wordBreak:"break-all", margin:0 }}>{imageUrl}</p>
            </div>}
            {hashtags.length > 0 && <div style={{ display:"flex", gap:6, flexWrap:"wrap" }}>
              {hashtags.map(h => <Badge key={h} variant="info" size="sm">{h}</Badge>)}
            </div>}
            <div style={{ padding:"10px 14px", borderRadius:9, background:"var(--info-bg)", border:"1px solid var(--info-border)" }}>
              <p style={{ fontSize:12, color:"var(--info-text)", margin:0 }}>
                Estimated cost so far: ₹{estimatedCost.toFixed(2)} — charged to Platform AI Budget. Tenant usage credits are never touched.
              </p>
            </div>
          </div>
        )}

        {/* Step 6 — Preview & Edit */}
        {step === 5 && (
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>Preview across selected channels:</p>
            {channels.length === 0 && <p style={{ fontSize:12, color:"var(--warning-text)" }}>No channels selected yet (Step 3).</p>}
            {channels.map(c => (
              <Card key={c} padding={16} style={{ background:"var(--surface-sunken)" }}>
                <p style={{ fontSize:11, fontWeight:700, color:"var(--text-tertiary)", margin:"0 0 8px", textTransform:"uppercase" }}>{c.replace("_"," ")} Preview</p>
                <Input label="Caption" value={caption} onChange={setCaption}/>
                <div style={{ marginTop:8, fontSize:12, color:"var(--text-secondary)" }}>CTA: {cta}</div>
              </Card>
            ))}
          </div>
        )}

        {/* Step 7 — Approval */}
        {step === 6 && (
          <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
            {(["draft","submit","approve_now"] as const).map(choice => (
              <label key={choice} style={{ display:"flex", alignItems:"center", gap:10, padding:"10px 14px",
                borderRadius:8, border: approvalChoice === choice ? "1px solid var(--accent)" : "1px solid var(--border)", cursor:"pointer" }}>
                <input type="radio" name="approval" checked={approvalChoice === choice} onChange={() => setApprovalChoice(choice)}/>
                <span style={{ fontSize:13, color:"var(--text-primary)" }}>
                  {choice === "draft" ? "Save Draft" : choice === "submit" ? "Submit for Approval" : "Approve Now (Super Admin)"}
                </span>
              </label>
            ))}
            <Btn variant="primary" size="sm" icon={<CheckCircle2 size={14}/>} loading={createAction.loading || submitApprovalAction.loading || approveAction.loading}
              onClick={handleApprovalStep}>Continue</Btn>
          </div>
        )}

        {/* Step 8 — Schedule */}
        {step === 7 && (
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
            <Input label="Date" type="date" value={scheduleDate} onChange={setScheduleDate}/>
            <Input label="Time" type="time" value={scheduleTime} onChange={setScheduleTime}/>
            {scheduleError && <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{scheduleError}</p>}
            <Btn variant="success" size="md" loading={scheduleAction.loading} onClick={handleSchedule}>Schedule Post</Btn>
          </div>
        )}

        {/* Footer nav (steps 1–6 use Next/Back; step 7/8 have their own actions) */}
        {step < 6 && (
          <div style={{ display:"flex", justifyContent:"space-between", marginTop:24, paddingTop:16, borderTop:"1px solid var(--border)" }}>
            <Btn variant="ghost" size="sm" disabled={!canPrev} onClick={() => setStep(s => s - 1)}>← Back</Btn>
            <Btn variant="primary" size="sm" disabled={!canNext} onClick={() => setStep(s => s + 1)}>Next →</Btn>
          </div>
        )}
      </Card>
    </AdminLayout>
  );
}

import React, { useCallback, useReducer, useState } from "react";
import {
  FlatList, KeyboardAvoidingView, Modal, Platform, StyleSheet, Text,
  TextInput, TouchableOpacity, View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import {
  aiConversationApi, catalogApi, homeServiceDraftApi, bookingConfirmApi,
  type AISession, type ServiceCategory, type ServiceOffering,
} from "../lib/api";
import {
  chatBookingReducer, initialChatBookingState, canonicalSlugsFor,
} from "../lib/chatBookingState";
import { CHAT_LANGUAGES, searchChatLanguages, type ChatLanguageOption } from "../lib/chatLanguages";
import { useTheme } from "../context/ThemeContext";
import type { Theme } from "../styles/theme";

/**
 * UX-06 Round 3 — real DeepSeek chat + the real, canonical booking journey
 * wired underneath it.
 *
 * Contract layer (see docs/design/ux-06-customer-app/deepseek-conversation-contract.md
 * for the full two-layer framing agreed with the coordinator):
 *   VERIFIED LIVE: customer login, chat-session creation, the backend AI-chat
 *   endpoint, service-category/offering tool calls, the structured response
 *   contract, graceful model-provider degradation.
 *   NOT YET VERIFIED: an actual DeepSeek model response using a real
 *   (non-placeholder) API key, reliable adherence to the customer-selected
 *   conversation language, language switching mid-conversation, and
 *   preservation of structured booking state after a language switch.
 *
 * Why the booking flow below is a structured picker UI, not text parsed out of
 * DeepSeek's reply: the /messages endpoint only returns `tools_called` (tool
 * NAMES) and a synthesized `reply` string — never the tools' raw JSON results.
 * Parsing IDs out of free text (which may itself be in a non-English selected
 * language) would violate "never let a translated label become a query value."
 * Instead, "Book a service" opens a REAL structured flow: catalogApi.categories()
 * -> catalogApi.categoryOfferings(slug) -> homeServiceDraftApi.start/updateFields/
 * serviceabilityCheck/priceEstimate/summary -> bookingConfirmApi.confirmHomeServiceBooking
 * (idempotent via a real Idempotency-Key header). Every ID sent onward comes
 * directly from a typed API response (see chatBookingState.ts) — never from a
 * chat bubble's display text.
 */
type Msg = { id:string; role:"user"|"assistant"; content:string };

// UX-07 Pass 3e: honest, real-state-derived progress for the guided booking
// flow (the only surface here with actual question->option turns; the free-
// text DeepSeek chat above has no backend-exposed step count -- see the file
// header comment on why). Ordered list of REAL steps that can occur; brand and
// offering-type steps are conditionally included only when the real backend
// data requires them (brands.length>0 / ac_repair), never assumed constant.
const BASE_STEPS = ["category","offering","issue_address","serviceability","price","confirm"] as const;
function stepsFor(hasBrandStep: boolean): string[] {
  const steps: string[] = [...BASE_STEPS];
  if (hasBrandStep) steps.splice(2, 0, "brand");
  return steps;
}
function currentStepIndex(booking: import("../lib/chatBookingState").ChatBookingState, hasBrandStep: boolean): number {
  const steps = stepsFor(hasBrandStep);
  if (!booking.category) return 0;
  if (!booking.offering) return steps.indexOf("category");
  if (hasBrandStep && !booking.brandId) return steps.indexOf("offering");
  if (!booking.issueDescription || !booking.addressLine) return steps.indexOf(hasBrandStep ? "brand" : "offering");
  if (booking.step === "not_yet_bookable" || (booking.serviceable === false)) return steps.indexOf("serviceability");
  if (!booking.priceSnapshot) return steps.indexOf("issue_address");
  if (!booking.selectedTier) return steps.indexOf("price");
  return steps.indexOf("confirm");
}
function progressLabel(booking: import("../lib/chatBookingState").ChatBookingState, hasBrandStep: boolean): string {
  const steps = stepsFor(hasBrandStep);
  const idx = currentStepIndex(booking, hasBrandStep);
  return `Step ${Math.min(idx + 1, steps.length)} of ${steps.length}`;
}
function progressPct(booking: import("../lib/chatBookingState").ChatBookingState, hasBrandStep: boolean): number {
  const steps = stepsFor(hasBrandStep);
  const idx = currentStepIndex(booking, hasBrandStep);
  return Math.round(((idx + 1) / steps.length) * 100);
}

interface Props {
  navigation?: { navigate: (screen: string, params?: unknown) => void };
  // UX-07 Pass 3d: category-handoff context from Home (see HomeScreen.tsx's
  // category tiles/search box, TabNavigator's AIAssistant route param). Only
  // ever a free-text label matched against the REAL backend category list
  // below (categoryMatchLabel) -- never assumed to equal a real slug/id, per
  // category-smartbot-handoff.md.
  route?: { params?: { initialCategoryLabel?: string } };
}

export function DeepSeekChatScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const s = makeStyles(theme);
  const [session, setSession]   = useState<AISession | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput]       = useState("");
  const [sending, setSending]   = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError]       = useState<string|null>(null);
  const [language, setLanguage] = useState<ChatLanguageOption>(CHAT_LANGUAGES[0]);
  const [langModal, setLangModal] = useState(false);
  const [langQuery, setLangQuery] = useState("");

  const [booking, dispatch] = useReducer(chatBookingReducer, initialChatBookingState());
  const [flowOpen, setFlowOpen]   = useState(false);
  const [categories, setCategories] = useState<ServiceCategory[]>([]);
  const [offerings, setOfferings]   = useState<ServiceOffering[]>([]);
  const [flowLoading, setFlowLoading] = useState(false);
  const [flowError, setFlowError]     = useState<string|null>(null);
  const [issueText, setIssueText]     = useState("");
  const [addressText, setAddressText] = useState("");
  const [cityText, setCityText]       = useState("");
  const [brands, setBrands]           = useState<{ brand_id:string; name:string }[]>([]);
  const categoryMatchLabel = route?.params?.initialCategoryLabel;
  const [handoffNotice, setHandoffNotice] = useState<string|null>(null);
  const [handoffConsumed, setHandoffConsumed] = useState(false);
  // UX-07 Pass 3e: collapsed by default per the guided-flow restructure --
  // see docs/workflow-rearchitecture/.../smartbot-answer-summary-behavior.md.
  const [summaryOpen, setSummaryOpen] = useState(false);

  const startSession = useCallback(async () => {
    setStarting(true); setError(null);
    try {
      const s = await aiConversationApi.createSession();
      setSession(s);
      setMessages([]);
    } catch (e:unknown) {
      setError(e instanceof Error ? e.message : "Could not start a conversation. Please try again.");
    } finally { setStarting(false); }
  }, []);

  // Every outgoing message goes through withLanguageInstruction inside
  // aiConversationApi.sendMessage — verified by a real unit test
  // (src/lib/__tests__/api.test.ts) that `language` is always passed through,
  // never sent without it once a non-English language is selected.
  async function send() {
    const text = input.trim();
    if (!text || !session || sending) return;
    setInput("");
    setMessages(m => [...m, { id:`u${m.length}`, role:"user", content:text }]);
    setSending(true); setError(null);
    try {
      const res = await aiConversationApi.sendMessage(session.id, text, language);
      setMessages(m => [...m, { id:`a${m.length}`, role:"assistant", content:res.reply }]);
      setSession(res.session);
    } catch (e:unknown) {
      setError(e instanceof Error ? e.message : "Message failed to send. Please try again.");
    } finally { setSending(false); }
  }

  async function openBookingFlow() {
    setFlowOpen(true); setFlowLoading(true); setFlowError(null); setHandoffNotice(null);
    dispatch({ type:"RESET", aiSessionId: session?.id ?? null });
    try {
      const res = await catalogApi.categories();
      setCategories(res.items);
      // UX-07 Pass 3d: if we arrived here carrying category context from
      // Home (a category tile tap or a search-box query), try to match it
      // against the REAL backend category list by name -- fuzzy substring,
      // case-insensitive, both directions. If found, auto-select it so the
      // customer is never asked "what service do you need" a second time.
      // If not found, fall back honestly to the full category list (no fake
      // selection) and show a small notice instead of silently dropping it.
      if (categoryMatchLabel && !handoffConsumed) {
        setHandoffConsumed(true);
        const q = categoryMatchLabel.trim().toLowerCase();
        const match = res.items.find(c =>
          c.name.toLowerCase().includes(q) || q.includes(c.name.toLowerCase()) ||
          c.slug.toLowerCase().replace(/_/g," ").includes(q));
        if (match) {
          setHandoffNotice(null);
          await pickCategory(match);
          return;
        }
        setHandoffNotice(`We couldn't find an exact match for "${categoryMatchLabel}" — please choose below.`);
        setIssueText(categoryMatchLabel);
      }
    } catch (e:unknown) {
      setFlowError(e instanceof Error ? e.message : "Could not load services.");
    } finally { setFlowLoading(false); }
  }

  // Auto-open the guided booking flow when arriving with category context
  // from Home, so the customer lands directly in the flow rather than on
  // the free-text chat screen first.
  React.useEffect(() => {
    if (!categoryMatchLabel || handoffConsumed || flowOpen) return;
    (async () => {
      if (!session) await startSession();
      openBookingFlow();
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [categoryMatchLabel, session]);

  async function pickCategory(cat: ServiceCategory) {
    dispatch({ type:"SELECT_CATEGORY", category: cat });
    setFlowLoading(true); setFlowError(null);
    try {
      const res = await catalogApi.categoryOfferings(cat.slug);
      setOfferings(res.items);
    } catch (e:unknown) {
      setFlowError(e instanceof Error ? e.message : "Could not load offerings for this category.");
    } finally { setFlowLoading(false); }
  }

  function pickOffering(off: ServiceOffering) {
    dispatch({ type:"SELECT_OFFERING", offering: off });
  }

  async function submitIssueAndAddress() {
    const slugs = canonicalSlugsFor(booking);
    if (!slugs) return;
    setFlowLoading(true); setFlowError(null);
    try {
      const draft = await homeServiceDraftApi.start(slugs.categorySlug, slugs.offeringSlug, session?.id);
      dispatch({ type:"DRAFT_STARTED", draft });
      dispatch({ type:"SET_ISSUE", issueDescription: issueText });
      dispatch({ type:"SET_ADDRESS", addressLine: addressText, city: cityText });
      // UX-06 Round 5 correction: real draft fields are `issue_summary`/
      // `issue_details` and a UUID `brand_id` -- NOT `issue_description`/
      // `address_line` (those were silently ignored by the real backend,
      // which only merges recognized keys — see bargain-contract-audit.md).
      // Brand is required for offerings with is_brand_required=true (real
      // for ac_repair) — fetched here using the draft's real MasterService
      // offering_id, then the customer must pick one before continuing.
      const brandRes = await catalogApi.brandsForService(draft.offering_id ?? "");
      setBrands(brandRes.brands);
      if (brandRes.brands.length > 0) {
        setFlowLoading(false);
        return; // wait for pickBrand() to continue the sequence
      }
      await homeServiceDraftApi.updateFields(draft.id, { issue_summary: issueText, city: cityText });
      await runServiceabilityThroughMatching(draft.id);
    } catch (e:unknown) {
      setFlowError(e instanceof Error ? e.message : "Could not process your request. Please try again.");
    } finally { setFlowLoading(false); }
  }

  async function pickBrand(brandId: string) {
    if (!booking.draft) return;
    dispatch({ type:"SET_BRAND", brandId });
    setFlowLoading(true); setFlowError(null);
    try {
      await homeServiceDraftApi.updateFields(booking.draft.id, {
        issue_summary: issueText, city: cityText, brand_id: brandId,
      });
      // UX-06 Recertification: real catalog quirk confirmed by the backend
      // team -- ac_repair has 2 type-scoped ServicePricingRule rows with no
      // global fallback, so offering_type_id must be set for pricing to
      // resolve, even though the offering reports is_type_required:false.
      // Real IDs (not invented), confirmed live: c86dfcf3-... (Rs775 base),
      // e27f6591-... (Rs425 base), both under this same brand/city.
      if (booking.offering?.slug === "ac_repair") {
        setFlowLoading(false);
        return; // wait for pickOfferingType() to continue
      }
      await runServiceabilityThroughMatching(booking.draft.id);
    } catch (e:unknown) {
      setFlowError(e instanceof Error ? e.message : "Could not process your request. Please try again.");
    } finally { setFlowLoading(false); }
  }

  const AC_REPAIR_TYPES = [
    { id:"c86dfcf3-53bd-4d83-bf0b-51257f382652", label:"Standard Service" },
    { id:"e27f6591-9b8d-4d57-93d0-8ed86c19c8af", label:"Basic Service" },
  ];

  async function pickOfferingType(offeringTypeId: string) {
    if (!booking.draft) return;
    dispatch({ type:"SET_OFFERING_TYPE", offeringTypeId });
    setFlowLoading(true); setFlowError(null);
    try {
      await homeServiceDraftApi.updateFields(booking.draft.id, { offering_type_id: offeringTypeId });
      await runServiceabilityThroughMatching(booking.draft.id);
    } catch (e:unknown) {
      setFlowError(e instanceof Error ? e.message : "Could not process your request. Please try again.");
    } finally { setFlowLoading(false); }
  }

  // Shared continuation: serviceability -> price-estimate -> match-and-price.
  // Real backend calls only; match-and-price is honestly allowed to fail
  // (see bargain-contract-audit.md) rather than being worked around.
  async function runServiceabilityThroughMatching(draftId: string) {
    const svc = await homeServiceDraftApi.serviceabilityCheck(draftId);
    dispatch({ type:"SERVICEABILITY_RESULT", serviceable: svc.serviceable, message: svc.message, draftStatus: svc.draft_status });
    if (svc.serviceable) {
      const price = await homeServiceDraftApi.priceEstimate(draftId);
      dispatch({ type:"PRICE_RESULT", priceSnapshot: price.price_snapshot ?? null, draftStatus: price.draft_status });
      try {
        const match = await homeServiceDraftApi.matchAndPrice(draftId);
        // UX-06 Recertification: real backend fix -- bargain_available is
        // always present now. false -> standard_price is the real price to
        // show/book at (no fake tiers, no invented fallback).
        dispatch({
          type:"MATCH_AND_PRICE_RESULT",
          priceOptions: match.selected_provider_price_options,
          bargainAvailable: match.bargain_available,
          standardPrice: match.standard_price,
        });
      } catch {
        dispatch({ type:"MATCH_AND_PRICE_UNAVAILABLE" });
      }
    }
  }

  async function selectPriceTier(tier: "low"|"mid"|"high"|"standard") {
    if (!booking.draft) return;
    setFlowLoading(true); setFlowError(null);
    try {
      await homeServiceDraftApi.confirmPriceChoice(booking.draft.id, tier);
      dispatch({ type:"TIER_SELECTED", tier });
    } catch (e:unknown) {
      setFlowError(e instanceof Error ? e.message : "Could not select this price option. Please try again.");
    } finally { setFlowLoading(false); }
  }

  async function confirmBooking() {
    if (!booking.draft) return;
    setFlowLoading(true); setFlowError(null);
    try {
      // UX-06 Recertification (2nd pass): the real `/confirm` route calls
      // mark_ready_for_confirmation(), which reads booking_summary (built by
      // /summary) rather than re-deriving it -- confirmed by the backend
      // team's own diagnosis. Call /summary explicitly first so
      // ready_for_confirmation is genuinely satisfied before /confirm, for
      // both the tier-based (low/mid/high) and the new standard-price path.
      await homeServiceDraftApi.summary(booking.draft.id);
      // Idempotency-Key: the draft ID itself is a stable, real, caller-owned
      // key — a retry of this exact call (e.g. after a network blip) hits the
      // same key and the backend's ConfirmationLockService returns the
      // existing booking instead of creating a duplicate. UX-06 Round 5:
      // corrected to the real customer-facing confirm route (see api.ts's
      // bookingConfirmApi comment / bargain-contract-audit.md for why the
      // Round 3/4 route was wrong).
      const result = await bookingConfirmApi.confirmHomeServiceBooking(booking.draft.id, booking.draft.id);
      if (!result.booking_number) throw new Error("Booking confirmation did not return a booking reference.");
      dispatch({ type:"SUBMITTED", bookingNumber: result.booking_number, jobNumber: result.job_number });
    } catch (e:unknown) {
      setFlowError(e instanceof Error ? e.message : "This service isn't available for booking in your area just yet. Please check back soon.");
    } finally { setFlowLoading(false); }
  }

  function goToBookingDetail() {
    setFlowOpen(false);
    if (navigation && booking.draft) {
      navigation.navigate("BookingDetail", { bookingId: booking.draft.id });
    }
  }

  if (!session) {
    return (
      <View style={[s.screen, s.center]}>
        <Text style={s.icon}>🤖</Text>
        <Text style={s.title}>Talk to ServiceOS Assistant</Text>
        <Text style={s.body}>Describe what you need in your own words — the assistant can look up services, pricing, and help you book.</Text>
        {error && <Text style={s.errorText}>{error}</Text>}
        <TouchableOpacity style={s.startBtn} onPress={startSession} disabled={starting} testID="chat-start"
          accessible accessibilityRole="button" accessibilityLabel="Start Conversation"
          accessibilityState={{ disabled: starting, busy: starting }}>
          <Text style={s.startBtnText}>{starting ? "Starting…" : "Start Conversation"}</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView style={s.screen} behavior={Platform.OS==="ios"?"padding":"height"}>
      <View style={s.header}>
        <TouchableOpacity style={s.bookBtn} onPress={openBookingFlow} testID="chat-book-service"
          accessible accessibilityRole="button" accessibilityLabel="Book a service">
          <Text style={s.bookBtnText}>📅 Book a service</Text>
        </TouchableOpacity>
        <TouchableOpacity style={s.langChip} onPress={()=>setLangModal(true)} testID="chat-language-btn"
          accessible accessibilityRole="button" accessibilityLabel={`Conversation language: ${language.englishName}. Tap to change`}>
          <Text style={s.langChipText}>{language.nativeName} ▾</Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={messages}
        keyExtractor={m=>m.id}
        contentContainerStyle={s.list}
        renderItem={({item}) => (
          <View style={[s.bubble, item.role==="user" ? s.bubbleUser : s.bubbleAssistant]}
            accessible accessibilityLabel={`${item.role === "user" ? "You" : "Assistant"} said: ${item.content}`}>
            <Text style={item.role==="user" ? s.bubbleUserText : s.bubbleAssistantText}>{item.content}</Text>
          </View>
        )}
      />

      {error && <Text style={s.errorText} accessibilityRole="alert" accessible>{error}</Text>}

      <View style={s.inputRow}>
        <TextInput
          style={s.input} value={input} onChangeText={setInput}
          placeholder="Type a message…" placeholderTextColor={theme.colors.textTertiary}
          testID="chat-input" accessibilityLabel="Message"
        />
        <TouchableOpacity style={s.sendBtn} onPress={send} disabled={sending} testID="chat-send"
          accessible accessibilityRole="button" accessibilityLabel="Send message" accessibilityState={{ disabled: sending, busy: sending }}>
          <Text style={s.sendBtnText}>{sending ? "…" : "Send"}</Text>
        </TouchableOpacity>
      </View>

      {/* ── Language selector — scoped to this chat screen only ────────────── */}
      <Modal visible={langModal} animationType="slide" onRequestClose={()=>setLangModal(false)}>
        <View style={s.langModal} accessibilityViewIsModal accessibilityRole="none">
          <TouchableOpacity onPress={()=>setLangModal(false)} accessible accessibilityRole="button"
            accessibilityLabel="Close language selector" style={{ alignSelf:"flex-end", padding:8 }}>
            <Text style={{ fontSize:18, color:theme.colors.textSecondary }}>✕</Text>
          </TouchableOpacity>
          <TextInput
            style={s.langSearch} value={langQuery} onChangeText={setLangQuery}
            placeholder="Search language…" placeholderTextColor={theme.colors.textTertiary}
            testID="chat-language-search" accessibilityLabel="Search language"
          />
          <FlatList
            data={searchChatLanguages(langQuery)}
            keyExtractor={l=>l.code}
            renderItem={({item}) => (
              <TouchableOpacity style={s.langRow} testID={`chat-language-option-${item.code}`}
                onPress={()=>{ setLanguage(item); setLangModal(false); setLangQuery(""); }}
                accessible accessibilityRole="button"
                accessibilityLabel={`${item.englishName} (${item.nativeName})`}
                accessibilityState={{ selected: item.code === language.code }}>
                <Text style={s.langRowNative}>{item.nativeName}</Text>
                <Text style={s.langRowEnglish}>{item.englishName} ({item.code})</Text>
              </TouchableOpacity>
            )}
          />
        </View>
      </Modal>

      {/* ── Real, canonical booking journey ─────────────────────────────────── */}
      <Modal visible={flowOpen} animationType="slide" onRequestClose={()=>setFlowOpen(false)}>
        <View style={s.flowModal} accessibilityViewIsModal>
          <View style={s.flowHeader}>
            <TouchableOpacity onPress={()=>setFlowOpen(false)} testID="booking-flow-back"
              accessible accessibilityRole="button" accessibilityLabel="Close guided booking"
              hitSlop={{ top:8, bottom:8, left:8, right:8 }}
              style={s.flowBackBtn}>
              <Ionicons name="chevron-back" size={22} color={theme.colors.textPrimary}/>
            </TouchableOpacity>
            <Text style={s.flowHeaderTitle} numberOfLines={1} accessibilityRole="header">
              {(booking.category?.name ?? categoryMatchLabel ?? "Book a Service")} Assistant
            </Text>
            <View style={{ width:32 }} />
          </View>

          {/* Progress indicator: derived only from real reducer step transitions
              (chatBookingState.ts) -- never a fabricated fixed step count. Some
              offerings have extra real steps (brand/offering-type), so the total
              is computed per-booking rather than assumed constant. */}
          {booking.step !== "idle" && booking.step !== "submitted" && (
            <View style={s.progressRow} accessible accessibilityLabel={progressLabel(booking, brands.length > 0)}>
              <Text style={s.progressText}>{progressLabel(booking, brands.length > 0)}</Text>
              <View style={s.progressTrack}>
                <View style={[s.progressFill, { width: `${progressPct(booking, brands.length > 0)}%` }]} />
              </View>
            </View>
          )}

          {/* Compact, collapsed-by-default summary of answers so far. Editing is
              honestly limited to "Start over" -- the real backend draft binds
              category/offering/brand at creation time, so there is no real
              partial-edit/re-validate contract to fabricate here. */}
          {(booking.category || booking.offering) && booking.step !== "submitted" && (
            <View style={s.summaryBox}>
              <TouchableOpacity onPress={()=>setSummaryOpen(o=>!o)} testID="booking-summary-toggle"
                accessible accessibilityRole="button"
                accessibilityLabel={summaryOpen ? "Collapse answers so far" : "Expand answers so far"}
                accessibilityState={{ expanded: summaryOpen }}
                style={s.summaryHeader}>
                <Text style={s.summaryHeaderText}>Answers so far</Text>
                <Ionicons name={summaryOpen ? "chevron-up" : "chevron-down"} size={16} color={theme.colors.textSecondary}/>
              </TouchableOpacity>
              {summaryOpen && (
                <View style={{ gap:6 }}>
                  {booking.category && <Text style={s.summaryLine}>Service: {booking.category.name}</Text>}
                  {booking.offering && <Text style={s.summaryLine}>Type: {booking.offering.name}</Text>}
                  {booking.issueDescription ? <Text style={s.summaryLine}>Issue: {booking.issueDescription}</Text> : null}
                  {booking.addressLine ? <Text style={s.summaryLine}>Address: {booking.addressLine}, {booking.city}</Text> : null}
                  <TouchableOpacity onPress={openBookingFlow} testID="booking-start-over"
                    accessible accessibilityRole="button" accessibilityLabel="Start over from the beginning">
                    <Text style={s.summaryEditLink}>Start over</Text>
                  </TouchableOpacity>
                </View>
              )}
            </View>
          )}

          {categoryMatchLabel && (
            <View style={s.handoffHeader} testID="booking-category-context">
              <Ionicons name="pricetag-outline" size={14} color={theme.colors.textInverse}/>
              <Text style={s.handoffHeaderText} numberOfLines={1}>{categoryMatchLabel} Assistant</Text>
            </View>
          )}
          {handoffNotice && <Text style={s.handoffNotice} testID="booking-handoff-notice">{handoffNotice}</Text>}
          {flowError && <Text style={s.errorText}>{flowError}</Text>}

          {booking.step === "submitted" ? (
            <View style={s.center}>
              <Text style={s.icon}>✅</Text>
              <Text style={s.title}>Booking Confirmed</Text>
              <Text style={s.body} testID="booking-reference">Reference: {booking.bookingNumber}</Text>
              <TouchableOpacity style={s.startBtn} onPress={goToBookingDetail} testID="chat-view-booking"
                accessible accessibilityRole="button" accessibilityLabel="View Booking">
                <Text style={s.startBtnText}>View Booking</Text>
              </TouchableOpacity>
            </View>
          ) : booking.priceSnapshot ? (
            <View style={{ gap:14, padding:16 }}>
              <Text style={s.title}>Review your booking</Text>
              <Text style={s.body}>{booking.category?.name} — {booking.offering?.name}</Text>
              <Text style={s.body}>{booking.issueDescription}</Text>
              <Text style={s.body}>{booking.addressLine}, {booking.city}</Text>
              {/* Price shown EXACTLY as the backend returned it — no client-side
                  recalculation, per the "server-returned values only" rule. */}
              <Text style={s.priceText} testID="booking-price">
                {booking.priceSnapshot.display_price ?? `₹${booking.priceSnapshot.final_price}`}
              </Text>

              {/* UX-06 Round 5, Workstream 4: honest bargain-available vs
                  bargain-unavailable presentation — never expose internal
                  floor/rule/error-code jargon either way. */}
              {booking.step === "not_yet_bookable" ? (
                <Text style={s.body} testID="booking-not-bookable">
                  This service isn't available for booking in your area just yet.
                  Please check back soon.
                </Text>
              ) : booking.bargainAvailable === false && booking.standardPrice != null && !booking.selectedTier ? (
                // UX-06 Recertification: real backend fix -- no BargainRule
                // configured for this offering, but the backend now returns a
                // real, authoritative standard_price (from ServicePricingRule)
                // instead of failing outright. Shown exactly as returned,
                // never recalculated client-side.
                <View style={{ gap:8 }}>
                  <Text style={s.priceText} testID="booking-standard-price">₹{booking.standardPrice}</Text>
                  <TouchableOpacity style={s.startBtn} onPress={()=>selectPriceTier("standard")}
                    disabled={flowLoading} testID="booking-continue-standard-price"
                    accessible accessibilityRole="button" accessibilityLabel="Continue with this price"
                    accessibilityState={{ disabled: flowLoading, busy: flowLoading }}>
                    <Text style={s.startBtnText}>{flowLoading ? "Please wait…" : "Continue with this price"}</Text>
                  </TouchableOpacity>
                </View>
              ) : booking.priceOptions && !booking.selectedTier ? (
                <View style={{ gap:8 }}>
                  <Text style={s.body}>Choose an option to continue:</Text>
                  {(["low","mid","high"] as const).map(tier => {
                    const tierLabel = tier === "mid" ? "Continue with this price" : tier === "low" ? "Lower estimate" : "Premium option";
                    return (
                      <TouchableOpacity key={tier} style={s.tierBtn} onPress={()=>selectPriceTier(tier)}
                        disabled={flowLoading} testID={`booking-tier-${tier}`}
                        accessible accessibilityRole="button" accessibilityLabel={tierLabel}
                        accessibilityState={{ disabled: flowLoading, busy: flowLoading }}>
                        <Text style={s.tierBtnText}>{tierLabel}</Text>
                      </TouchableOpacity>
                    );
                  })}
                </View>
              ) : booking.selectedTier ? (
                <TouchableOpacity style={s.startBtn} onPress={confirmBooking} disabled={flowLoading} testID="chat-confirm-booking"
                  accessible accessibilityRole="button" accessibilityLabel="Confirm Booking"
                  accessibilityState={{ disabled: flowLoading, busy: flowLoading }}>
                  <Text style={s.startBtnText}>{flowLoading ? "Confirming…" : "Confirm Booking"}</Text>
                </TouchableOpacity>
              ) : (
                <Text style={s.body}>Checking availability…</Text>
              )}
              <Text style={s.onSiteNote}>You pay the technician on-site — ServiceOS does not process this payment.</Text>
            </View>
          ) : booking.step === "serviceability_checked" || booking.serviceable === false ? (
            <View style={{ gap:14, padding:16 }}>
              <Text style={s.body} testID="booking-serviceability">{booking.serviceabilityMessage}</Text>
              {flowLoading && <Text style={s.body}>Loading price…</Text>}
            </View>
          ) : booking.draft && brands.length > 0 && !booking.brandId ? (
            <FlatList
              data={brands} keyExtractor={b=>b.brand_id}
              ListHeaderComponent={<Text style={[s.title,{padding:16}]}>Select your appliance brand</Text>}
              renderItem={({item}) => (
                <TouchableOpacity style={s.langRow} onPress={()=>pickBrand(item.brand_id)} testID={`brand-${item.brand_id}`}
                  accessible accessibilityRole="button" accessibilityLabel={`Select brand: ${item.name}`}>
                  <Text style={s.langRowNative}>{item.name}</Text>
                </TouchableOpacity>
              )}
            />
          ) : booking.draft && booking.brandId && booking.offering?.slug === "ac_repair" && !booking.offeringTypeId ? (
            <FlatList
              data={AC_REPAIR_TYPES} keyExtractor={t=>t.id}
              ListHeaderComponent={<Text style={[s.title,{padding:16}]}>Select service type</Text>}
              renderItem={({item}) => (
                <TouchableOpacity style={s.langRow} onPress={()=>pickOfferingType(item.id)} testID={`offering-type-${item.id}`}
                  accessible accessibilityRole="button" accessibilityLabel={`Select service type: ${item.label}`}>
                  <Text style={s.langRowNative}>{item.label}</Text>
                </TouchableOpacity>
              )}
            />
          ) : booking.offering ? (
            <View style={{ gap:12, padding:16 }}>
              <Text style={s.title}>Tell us more</Text>
              <TextInput style={s.input} value={issueText} onChangeText={setIssueText}
                placeholder="Describe the issue" placeholderTextColor={theme.colors.textTertiary}
                testID="booking-issue-input" accessibilityLabel="Describe the issue"/>
              <TextInput style={s.input} value={addressText} onChangeText={setAddressText}
                placeholder="Address" placeholderTextColor={theme.colors.textTertiary}
                testID="booking-address-input" accessibilityLabel="Address"/>
              <TextInput style={s.input} value={cityText} onChangeText={setCityText}
                placeholder="City" placeholderTextColor={theme.colors.textTertiary}
                testID="booking-city-input" accessibilityLabel="City"/>
              <TouchableOpacity style={s.startBtn} onPress={submitIssueAndAddress} disabled={flowLoading} testID="booking-check-serviceability"
                accessible accessibilityRole="button" accessibilityLabel="Check availability"
                accessibilityState={{ disabled: flowLoading, busy: flowLoading }}>
                <Text style={s.startBtnText}>{flowLoading ? "Checking…" : "Check availability"}</Text>
              </TouchableOpacity>
            </View>
          ) : booking.category ? (
            <FlatList
              data={offerings} keyExtractor={o=>o.id}
              ListHeaderComponent={<Text style={[s.title,{padding:16}]}>Choose a service</Text>}
              renderItem={({item}) => (
                <View style={[s.langRow, { flexDirection:"row", alignItems:"center", justifyContent:"space-between" }]}>
                  <TouchableOpacity style={{ flex:1 }} onPress={()=>pickOffering(item)} testID={`offering-${item.slug}`}
                    accessible accessibilityRole="button" accessibilityLabel={`Select service: ${item.name}`}>
                    <Text style={s.langRowNative}>{item.name}</Text>
                  </TouchableOpacity>
                  {booking.category && (
                    <TouchableOpacity
                      onPress={()=>{ setFlowOpen(false); navigation?.navigate("ServiceDetail", { categorySlug: booking.category!.slug, offeringSlug: item.slug }); }}
                      testID={`offering-details-${item.slug}`}
                      accessible accessibilityRole="button" accessibilityLabel={`View details for ${item.name}`}>
                      <Text style={{ color:theme.colors.accent, fontSize:theme.font.size.sm }}>Details ⓘ</Text>
                    </TouchableOpacity>
                  )}
                </View>
              )}
            />
          ) : (
            <FlatList
              data={categories} keyExtractor={c=>c.id}
              ListHeaderComponent={<Text style={[s.title,{padding:16}]}>What do you need help with?</Text>}
              renderItem={({item}) => (
                <TouchableOpacity style={s.langRow} onPress={()=>pickCategory(item)} testID={`category-${item.slug}`}
                  accessible accessibilityRole="button" accessibilityLabel={`Select category: ${item.name}`}>
                  <Text style={s.langRowNative}>{item.name}</Text>
                </TouchableOpacity>
              )}
            />
          )}
        </View>
      </Modal>
    </KeyboardAvoidingView>
  );
}

// UX-07 Round 4 Pass 2: DeepSeekChatScreen (the SmartBot surface) migrated
// off the static `theme` import onto useTheme()/makeStyles(theme) -- the
// most important dark-mode surface per this round's mission. Bubbles now
// use the dedicated bubbleCustomer*/bubbleAssistant* tokens (readable in
// both modes, distinct from raw brand/surfaceSunken which flattened
// contrast in dark mode) and "#fff" literals were replaced with
// theme.colors.textInverse / bubbleCustomerText so button/bubble text
// stays legible against the dark brand color too. Long Hindi/Punjabi
// bubble text is unaffected by these changes (still auto-sizing maxWidth
// 80% + wrapping Text, no fixed height).
function makeStyles(theme: Theme) {
  return StyleSheet.create({
    screen: { flex:1, backgroundColor:theme.colors.bg },
    center: { alignItems:"center", justifyContent:"center", padding:32, gap:14 },
    icon:   { fontSize:48 },
    title:  { fontSize:theme.font.size.xl, fontWeight:"700", color:theme.colors.textPrimary, textAlign:"center" },
    body:   { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, textAlign:"center", lineHeight:20 },
    priceText: { fontSize:theme.font.size.xxxl, fontWeight:"800", color:theme.colors.brand, textAlign:"center" },
    tierBtn: { borderWidth:1, borderColor:theme.colors.border, borderRadius:theme.radius.lg,
               padding:14, backgroundColor:theme.colors.surfaceSunken },
    tierBtnText: { fontSize:theme.font.size.base, fontWeight:"600", color:theme.colors.textPrimary, textAlign:"center" },
    onSiteNote: { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, textAlign:"center" },
    errorText: { color:theme.colors.dangerText, fontSize:theme.font.size.sm, textAlign:"center", paddingHorizontal:16 },
    startBtn: { backgroundColor:theme.colors.brand, borderRadius:theme.radius.lg, paddingVertical:14, paddingHorizontal:28, minHeight:44 },
    startBtnText: { color:theme.colors.textInverse, fontWeight:"700", fontSize:theme.font.size.base, textAlign:"center" },
    header: { flexDirection:"row", justifyContent:"space-between", alignItems:"center", padding:10, borderBottomWidth:1, borderBottomColor:theme.colors.border, backgroundColor:theme.colors.surface },
    bookBtn: { paddingHorizontal:12, paddingVertical:6, minHeight:36, justifyContent:"center", borderRadius:theme.radius.full, backgroundColor:theme.colors.brand },
    bookBtnText: { fontSize:theme.font.size.sm, fontWeight:"700", color:theme.colors.textInverse },
    langChip: { paddingHorizontal:12, paddingVertical:6, minHeight:36, justifyContent:"center", borderRadius:theme.radius.full, backgroundColor:theme.colors.surfaceSunken },
    langChipText: { fontSize:theme.font.size.sm, fontWeight:"600", color:theme.colors.textPrimary },
    list: { padding:14, gap:10 },
    bubble: { maxWidth:"80%", borderRadius:theme.radius.lg, padding:12 },
    bubbleUser: { alignSelf:"flex-end", backgroundColor:theme.colors.bubbleCustomer },
    bubbleAssistant: { alignSelf:"flex-start", backgroundColor:theme.colors.bubbleAssistant },
    bubbleUserText: { color:theme.colors.bubbleCustomerText, fontSize:theme.font.size.base },
    bubbleAssistantText: { color:theme.colors.bubbleAssistantText, fontSize:theme.font.size.base },
    inputRow: { flexDirection:"row", gap:8, padding:12, borderTopWidth:1, borderTopColor:theme.colors.border, backgroundColor:theme.colors.surface },
    input: { flex:1, height:44, borderWidth:1, borderColor:theme.colors.border, borderRadius:theme.radius.lg,
             paddingHorizontal:14, fontSize:theme.font.size.base, color:theme.colors.textPrimary,
             backgroundColor:theme.colors.surfaceSunken },
    sendBtn: { justifyContent:"center", paddingHorizontal:18, minHeight:44, borderRadius:theme.radius.lg, backgroundColor:theme.colors.brand },
    sendBtnText: { color:theme.colors.textInverse, fontWeight:"700" },
    langModal: { flex:1, backgroundColor:theme.colors.bg, paddingTop:60, paddingHorizontal:16 },
    flowModal: { flex:1, backgroundColor:theme.colors.bg, paddingTop:60 },
    handoffHeader: { flexDirection:"row", alignItems:"center", gap:6, backgroundColor:theme.colors.brand,
                     paddingVertical:8, paddingHorizontal:16 },
    handoffHeaderText: { fontSize:theme.font.size.sm, fontWeight:"700", color:theme.colors.textInverse },
    handoffNotice: { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, textAlign:"center",
                     paddingHorizontal:16, paddingTop:8 },
    langSearch: { height:44, borderWidth:1, borderColor:theme.colors.border, borderRadius:theme.radius.lg,
                  paddingHorizontal:14, fontSize:theme.font.size.base, color:theme.colors.textPrimary,
                  backgroundColor:theme.colors.surfaceSunken, marginBottom:12, marginHorizontal:16 },
    langRow: { paddingVertical:12, paddingHorizontal:16, minHeight:44, borderBottomWidth:1, borderBottomColor:theme.colors.border },
    langRowNative: { fontSize:theme.font.size.base, fontWeight:"600", color:theme.colors.textPrimary },
    langRowEnglish: { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, marginTop:2 },
    flowHeader: { flexDirection:"row", alignItems:"center", justifyContent:"space-between",
                  paddingHorizontal:12, paddingBottom:10, gap:8 },
    flowBackBtn: { width:32, height:32, alignItems:"center", justifyContent:"center" },
    flowHeaderTitle: { flex:1, textAlign:"center", fontSize:theme.font.size.base, fontWeight:"700",
                       color:theme.colors.textPrimary },
    progressRow: { paddingHorizontal:16, paddingBottom:10, gap:6 },
    progressText: { fontSize:theme.font.size.xs, color:theme.colors.textSecondary, fontWeight:"600" },
    progressTrack: { height:6, borderRadius:3, backgroundColor:theme.colors.surfaceSunken, overflow:"hidden" },
    progressFill: { height:6, borderRadius:3, backgroundColor:theme.colors.brand },
    summaryBox: { marginHorizontal:16, marginBottom:10, borderWidth:1, borderColor:theme.colors.border,
                  borderRadius:theme.radius.lg, padding:12, backgroundColor:theme.colors.surface, gap:8 },
    summaryHeader: { flexDirection:"row", alignItems:"center", justifyContent:"space-between", minHeight:24 },
    summaryHeaderText: { fontSize:theme.font.size.sm, fontWeight:"700", color:theme.colors.textPrimary },
    summaryLine: { fontSize:theme.font.size.xs, color:theme.colors.textSecondary },
    summaryEditLink: { fontSize:theme.font.size.xs, fontWeight:"700", color:theme.colors.accent, paddingTop:4 },
  });
}

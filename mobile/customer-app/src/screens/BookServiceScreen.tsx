import React, { useState } from "react";
import {
  Alert, KeyboardAvoidingView, Platform,
  ScrollView, StyleSheet, Text, TextInput,
  TouchableOpacity, View,
} from "react-native";
import { useAction } from "../hooks/useApi";
import { bookingsApi } from "../lib/api";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { theme, gs } from "../styles/theme";
import {
  SERVICE_CATEGORIES, JOB_TYPE_META,
  isSingleTypeCategory, getSingleType,
  servicesForCategoryAndType,
  type ServiceJobType, type ServiceItem, type ServiceCategory,
} from "../lib/serviceTypes";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

type Params = { categoryId?:string; jobType?:ServiceJobType };
type Props  = NativeStackScreenProps<{ BookService:Params }, "BookService">;

type Step = "category" | "type" | "service" | "schedule" | "confirm";

const CITIES = ["Mumbai","Delhi","Bangalore","Hyderabad","Pune","Chennai","Ahmedabad","Kolkata"];

export function BookServiceScreen({ route, navigation }: Props) {
  const [step,     setStep]     = useState<Step>(route.params?.categoryId ? "type" : "category");
  const [category, setCategory] = useState<ServiceCategory | null>(
    route.params?.categoryId
      ? SERVICE_CATEGORIES.find(c => c.id === route.params!.categoryId!) ?? null
      : null
  );
  const [jobType,  setJobType]  = useState<ServiceJobType | null>(route.params?.jobType ?? null);
  const [service,  setService]  = useState<ServiceItem | null>(null);
  const [date,     setDate]     = useState("");
  const [time,     setTime]     = useState("10:00");
  const [address,  setAddress]  = useState("");
  const [city,     setCity]     = useState("");
  const [notes,    setNotes]    = useState("");

  const bookAction = useAction((payload:Record<string,unknown>) =>
    bookingsApi.create(payload as Parameters<typeof bookingsApi.create>[0])
  );

  function selectCategory(cat: ServiceCategory) {
    setCategory(cat);
    // If category only has one type, skip the type selector
    if (isSingleTypeCategory(cat.id)) {
      setJobType(getSingleType(cat.id));
      setStep("service");
    } else {
      setStep("type");
    }
  }

  function selectType(type: ServiceJobType) {
    setJobType(type);
    setStep("service");
  }

  // ── Step 1: Category ──────────────────────────────────────────────────────
  function renderCategory() {
    return (
      <ScrollView contentContainerStyle={s.content}>
        <Text style={s.title}>What service do you need?</Text>
        <Text style={s.sub}>Pick a category and we'll show you the right options.</Text>
        <View style={s.grid}>
          {SERVICE_CATEGORIES.map(cat => (
            <TouchableOpacity key={cat.id} style={s.catCard}
              onPress={() => selectCategory(cat)} activeOpacity={0.8}>
              <Text style={s.catIcon}>{cat.icon}</Text>
              <Text style={s.catName}>{cat.name}</Text>
              {/* Show available type badges */}
              <View style={s.typeBadges}>
                {cat.availableTypes.map(t => (
                  <View key={t} style={[s.typeBadge, { backgroundColor:JOB_TYPE_META[t].bg }]}>
                    <Text style={[s.typeBadgeText, { color:JOB_TYPE_META[t].color }]}>
                      {JOB_TYPE_META[t].icon}
                    </Text>
                  </View>
                ))}
              </View>
            </TouchableOpacity>
          ))}
        </View>
      </ScrollView>
    );
  }

  // ── Step 2: Type (only if category has >1 type) ───────────────────────────
  function renderType() {
    if (!category) return null;
    return (
      <ScrollView contentContainerStyle={s.content}>
        <TouchableOpacity style={s.back} onPress={() => setStep("category")}>
          <Text style={s.backText}>← {category.name}</Text>
        </TouchableOpacity>
        <Text style={s.title}>What do you need?</Text>
        <View style={s.typeRow}>
          {category.availableTypes.map(type => {
            const meta = JOB_TYPE_META[type];
            return (
              <TouchableOpacity key={type} style={[s.typeCard, { borderColor:meta.border, backgroundColor:meta.bg }]}
                onPress={() => selectType(type)} activeOpacity={0.85}>
                <Text style={s.typeIcon}>{meta.icon}</Text>
                <Text style={[s.typeLabel, { color:meta.color }]}>{meta.label}</Text>
                <Text style={s.typeTagline}>{meta.tagline}</Text>
                {/* Show type-specific price hint */}
                {type === "repair" && (
                  <Text style={[s.priceHint, { color:meta.color }]}>Visit fee only • Quote after inspection</Text>
                )}
                {type === "maintenance" && (
                  <Text style={[s.priceHint, { color:meta.color }]}>Fixed price shown upfront</Text>
                )}
                {type === "consultation" && (
                  <Text style={[s.priceHint, { color:meta.color }]}>Fixed consult fee • Written report</Text>
                )}
              </TouchableOpacity>
            );
          })}
        </View>
        {/* If category only has one type, we'd never reach this screen — safety */}
        <View style={s.helpBox}>
          <Text style={s.helpText}>
            Not sure which to pick?{"\n"}
            If something is broken → <Text style={{ fontWeight:"700" }}>Fix a Problem</Text>{"\n"}
            Routine care → <Text style={{ fontWeight:"700" }}>Book a Service</Text>{"\n"}
            Want an expert opinion first → <Text style={{ fontWeight:"700" }}>Get Expert Advice</Text>
          </Text>
        </View>
      </ScrollView>
    );
  }

  // ── Step 3: Service selection ─────────────────────────────────────────────
  function renderService() {
    if (!category || !jobType) return null;
    const meta     = JOB_TYPE_META[jobType];
    const services = servicesForCategoryAndType(category.id, jobType);
    const canGoBack = (category.availableTypes.length > 1);

    return (
      <ScrollView contentContainerStyle={s.content}>
        <TouchableOpacity style={s.back}
          onPress={() => canGoBack ? setStep("type") : setStep("category")}>
          <Text style={s.backText}>← {canGoBack ? meta.label : category.name}</Text>
        </TouchableOpacity>
        <Text style={s.title}>{category.name}</Text>
        <View style={[s.typeBanner, { backgroundColor:meta.bg, borderColor:meta.border }]}>
          <Text style={[s.typeBannerText, { color:meta.color }]}>
            {meta.icon}  {meta.label}
          </Text>
        </View>
        {services.map(sv => (
          <TouchableOpacity key={sv.name} style={s.serviceCard}
            onPress={() => { setService(sv); setStep("schedule"); }} activeOpacity={0.85}>
            <Text style={s.serviceIcon}>{sv.icon}</Text>
            <View style={{ flex:1 }}>
              <Text style={s.serviceName}>{sv.name}</Text>
              <Text style={s.serviceDesc} numberOfLines={2}>{sv.description}</Text>
              <View style={[gs.row, { marginTop:6, gap:8, flexWrap:"wrap" }]}>
                <Text style={s.duration}>⏱ {sv.duration}</Text>
                {sv.jobType === "repair" && sv.visitFee && (
                  <View style={s.pill}><Text style={[s.pillTxt, { color:meta.color }]}>₹{sv.visitFee} visit fee</Text></View>
                )}
                {sv.jobType === "maintenance" && sv.fixedPrice && (
                  <View style={[s.pill, { backgroundColor:meta.bg }]}>
                    <Text style={[s.pillTxt, { color:meta.color }]}>₹{sv.fixedPrice.toLocaleString("en-IN")}</Text>
                  </View>
                )}
                {sv.jobType === "consultation" && sv.consultFee && (
                  <View style={[s.pill, { backgroundColor:meta.bg }]}>
                    <Text style={[s.pillTxt, { color:meta.color }]}>₹{sv.consultFee} consult</Text>
                  </View>
                )}
              </View>
              {/* Show checklist preview for maintenance */}
              {sv.checklist && sv.checklist.length > 0 && (
                <Text style={s.checklistPreview}>
                  Includes: {sv.checklist.slice(0,2).join(", ")}{sv.checklist.length>2?` +${sv.checklist.length-2} more`:""}
                </Text>
              )}
            </View>
            <Text style={{ fontSize:20, color:theme.colors.textTertiary }}>›</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    );
  }

  // ── Step 4: Schedule ──────────────────────────────────────────────────────
  function renderSchedule() {
    if (!service || !jobType || !category) return null;
    const meta = JOB_TYPE_META[jobType];
    return (
      <KeyboardAvoidingView style={{ flex:1 }} behavior={Platform.OS==="ios"?"padding":"height"}>
        <ScrollView contentContainerStyle={s.content}>
          <TouchableOpacity style={s.back} onPress={() => setStep("service")}>
            <Text style={s.backText}>← {service.name}</Text>
          </TouchableOpacity>

          {/* Service summary */}
          <View style={[s.summary, { borderColor:meta.border, backgroundColor:meta.bg }]}>
            <View style={[gs.row, { gap:12 }]}>
              <Text style={{ fontSize:28 }}>{service.icon}</Text>
              <View style={{ flex:1 }}>
                <Text style={[s.summaryTitle, { color:meta.color }]}>{service.name}</Text>
                <Text style={s.summaryCategory}>{category.name}  ·  ⏱ {service.duration}</Text>
              </View>
            </View>

            {/* Pricing explanation — varies by type */}
            {service.jobType === "repair" && (
              <View style={s.priceBox}>
                <Text style={s.priceBoxTitle}>🔧 Repair Pricing</Text>
                <Text style={s.priceBoxLine}>• Pay <Text style={{ fontWeight:"700" }}>₹{service.visitFee} visit fee</Text> now to book</Text>
                <Text style={s.priceBoxLine}>• Technician inspects the problem on-site</Text>
                <Text style={s.priceBoxLine}>• You receive a <Text style={{ fontWeight:"700" }}>quote in the app</Text> before any work starts</Text>
                <Text style={s.priceBoxLine}>• <Text style={{ fontWeight:"700" }}>Approve or decline</Text> — your choice, no pressure</Text>
                <Text style={s.priceBoxLine}>• Visit fee is adjusted against the final bill if approved</Text>
              </View>
            )}
            {service.jobType === "maintenance" && service.fixedPrice && (
              <View style={[s.priceBox, { backgroundColor:"#F0FDF4", borderColor:"#BBF7D0" }]}>
                <Text style={[s.priceBoxTitle, { color:"#16A34A" }]}>✅ Fixed Price: ₹{service.fixedPrice.toLocaleString("en-IN")}</Text>
                <Text style={s.priceBoxLine}>Complete price with no hidden charges.</Text>
                {service.checklist && (
                  <Text style={s.priceBoxLine}>
                    Includes: {service.checklist.join(" · ")}
                  </Text>
                )}
              </View>
            )}
            {service.jobType === "consultation" && service.consultFee && (
              <View style={[s.priceBox, { backgroundColor:"#F5F3FF", borderColor:"#DDD6FE" }]}>
                <Text style={[s.priceBoxTitle, { color:"#7C3AED" }]}>📋 Consultation: ₹{service.consultFee}</Text>
                <Text style={s.priceBoxLine}>• Expert gives you a detailed written report</Text>
                <Text style={s.priceBoxLine}>• Includes repair/work estimate if anything is found</Text>
                <Text style={s.priceBoxLine}>• Fee applies regardless of outcome</Text>
              </View>
            )}
          </View>

          {/* Date / time */}
          <Card style={{ gap:14 }}>
            <Text style={gs.label}>When?</Text>
            <View style={gs.row}>
              <View style={{ flex:1 }}>
                <Text style={s.fieldLabel}>Date *</Text>
                <TextInput style={s.input} value={date} onChangeText={setDate}
                  placeholder="DD-MM-YYYY" placeholderTextColor={theme.colors.textTertiary} />
              </View>
              <View style={{ width:14 }}/>
              <View style={{ flex:1 }}>
                <Text style={s.fieldLabel}>Time</Text>
                <TextInput style={s.input} value={time} onChangeText={setTime}
                  placeholder="10:00" placeholderTextColor={theme.colors.textTertiary}
                  keyboardType="numbers-and-punctuation" />
              </View>
            </View>
          </Card>

          {/* City */}
          <Card style={{ gap:10 }}>
            <Text style={gs.label}>City *</Text>
            <View style={{ flexDirection:"row", flexWrap:"wrap", gap:8 }}>
              {CITIES.map(c => (
                <TouchableOpacity key={c} onPress={() => setCity(c)} activeOpacity={0.8}
                  style={[s.chip, city===c && { backgroundColor:theme.colors.brand, borderColor:theme.colors.brand }]}>
                  <Text style={[s.chipText, city===c && { color:"#fff" }]}>{c}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </Card>

          {/* Address */}
          <Card style={{ gap:10 }}>
            <Text style={gs.label}>Address *</Text>
            <TextInput style={[s.input, { height:80, paddingTop:10 }]}
              value={address} onChangeText={setAddress}
              placeholder="Flat/house number, building, street, landmark…"
              placeholderTextColor={theme.colors.textTertiary}
              multiline numberOfLines={3} textAlignVertical="top" />
            <TextInput style={s.input} value={notes} onChangeText={setNotes}
              placeholder={
                service.jobType === "repair"
                  ? "Describe the problem — when it started, what you've tried (helps technician prepare)"
                  : "Any special instructions (optional)"
              }
              placeholderTextColor={theme.colors.textTertiary} />
          </Card>

          <Button label="Review Booking →" variant="primary" size="lg" fullWidth
            disabled={!date || !city || !address.trim()}
            onPress={() => setStep("confirm")} />
        </ScrollView>
      </KeyboardAvoidingView>
    );
  }

  // ── Step 5: Confirm ───────────────────────────────────────────────────────
  async function handleBook() {
    if (!service || !date || !city || !address.trim()) return;
    const parts = date.split("-");
    const d = parts[0]?.padStart(2,"0") ?? "01";
    const m = parts[1]?.padStart(2,"0") ?? "01";
    const y = parts[2] ?? String(new Date().getFullYear());
    const scheduled_at = `${y}-${m}-${d}T${time || "10:00"}:00`;

    const res = await bookAction.execute({
      service_type:    service.name,
      service_category:category!.id,
      job_type:        service.jobType,
      scheduled_at,
      address:         address.trim(),
      city,
      notes:           notes.trim() || undefined,
    });

    if (res) {
      const msg = service.jobType === "repair"
        ? `Booking ${res.booking_number} confirmed.\n\nThe technician will inspect the problem and send you a repair quote before starting any work.`
        : service.jobType === "consultation"
        ? `Booking ${res.booking_number} confirmed.\n\nYou'll receive a detailed expert report after the visit.`
        : `Booking ${res.booking_number} confirmed.`;

      Alert.alert("Booking Confirmed 🎉", msg, [
        { text:"View Booking", onPress:() => navigation.navigate("BookingDetail" as never, { bookingId:res.id } as never) },
        { text:"Home", onPress:() => navigation.navigate("Home" as never) },
      ]);
    }
  }

  function renderConfirm() {
    if (!service || !category || !jobType) return null;
    const meta = JOB_TYPE_META[jobType];
    const price = service.jobType==="repair" ? service.visitFee
      : service.jobType==="maintenance"      ? service.fixedPrice
      : service.consultFee;

    return (
      <ScrollView contentContainerStyle={s.content}>
        <TouchableOpacity style={s.back} onPress={() => setStep("schedule")}>
          <Text style={s.backText}>← Edit details</Text>
        </TouchableOpacity>
        <Text style={s.title}>Confirm Booking</Text>

        <Card style={{ gap:12 }}>
          <View style={[gs.row, { gap:12 }]}>
            <Text style={{ fontSize:28 }}>{service.icon}</Text>
            <View style={{ flex:1 }}>
              <Text style={s.serviceName}>{service.name}</Text>
              <Text style={s.serviceCategory}>{category.name}</Text>
            </View>
            <View style={[s.pill, { backgroundColor:meta.bg }]}>
              <Text style={[s.pillTxt, { color:meta.color }]}>{meta.icon} {meta.label}</Text>
            </View>
          </View>
          {[
            { label:"📅 Date & Time", value:`${date} at ${time}` },
            { label:"📍 City",        value:city },
            { label:"🏠 Address",     value:address },
            ...(notes ? [{ label:"📝 Notes", value:notes }] : []),
          ].map(row => (
            <View key={row.label} style={[gs.row, { gap:10, paddingTop:10,
              borderTopWidth:1, borderTopColor:theme.colors.border }]}>
              <Text style={{ fontSize:theme.font.size.sm, color:theme.colors.textSecondary, width:120 }}>{row.label}</Text>
              <Text style={{ fontSize:theme.font.size.sm, fontWeight:"500", color:theme.colors.textPrimary, flex:1 }}
                numberOfLines={3}>{row.value}</Text>
            </View>
          ))}
        </Card>

        <Card style={{ gap:8 }}>
          <Text style={gs.label}>You Pay Now</Text>
          <View style={[gs.row, { justifyContent:"space-between" }]}>
            <Text style={{ fontSize:theme.font.size.base, color:theme.colors.textSecondary }}>
              {service.jobType==="repair" ? "Visit & assessment fee" : service.jobType==="consultation" ? "Consultation fee" : "Service price"}
            </Text>
            <Text style={{ fontSize:theme.font.size.xxl, fontWeight:"800", color:theme.colors.brand }}>
              ₹{price?.toLocaleString("en-IN")}
            </Text>
          </View>
          {service.jobType === "repair" && (
            <View style={[s.priceBox, { marginTop:4 }]}>
              <Text style={s.priceBoxLine}>
                ⚠ Repair quote will be sent <Text style={{ fontWeight:"700" }}>before any work begins</Text>.
                Visit fee is adjusted against final bill.
              </Text>
            </View>
          )}
        </Card>

        {bookAction.error && (
          <View style={{ backgroundColor:theme.colors.dangerBg, borderRadius:theme.radius.md,
            padding:12, borderWidth:1, borderColor:theme.colors.dangerBorder }}>
            <Text style={{ fontSize:theme.font.size.sm, color:theme.colors.dangerText }}>{bookAction.error}</Text>
          </View>
        )}

        <Button label="Confirm Booking" variant="primary" size="lg" fullWidth
          loading={bookAction.loading} onPress={handleBook} />
        <Button label="Go Back" variant="ghost" size="md" fullWidth
          onPress={() => setStep("schedule")} />
      </ScrollView>
    );
  }

  return (
    <View style={gs.screen}>
      {step === "category" && renderCategory()}
      {step === "type"     && renderType()}
      {step === "service"  && renderService()}
      {step === "schedule" && renderSchedule()}
      {step === "confirm"  && renderConfirm()}
    </View>
  );
}

const s = StyleSheet.create({
  content:         { padding:theme.spacing.base, gap:14, paddingBottom:40 },
  title:           { fontSize:theme.font.size.xxl, fontWeight:"800", color:theme.colors.textPrimary },
  sub:             { fontSize:theme.font.size.base, color:theme.colors.textSecondary, lineHeight:22 },
  back:            { flexDirection:"row", alignItems:"center", marginBottom:4 },
  backText:        { fontSize:theme.font.size.base, color:theme.colors.accent, fontWeight:"600" },
  // Category grid
  grid:            { flexDirection:"row", flexWrap:"wrap", gap:10 },
  catCard:         { width:"47%", backgroundColor:theme.colors.surface, borderRadius:theme.radius.lg,
                     padding:14, alignItems:"center", gap:8, ...theme.shadow.sm,
                     borderWidth:1, borderColor:theme.colors.border },
  catIcon:         { fontSize:30 },
  catName:         { fontSize:theme.font.size.sm, fontWeight:"700", color:theme.colors.textPrimary, textAlign:"center" },
  typeBadges:      { flexDirection:"row", gap:4 },
  typeBadge:       { width:22, height:22, borderRadius:11, alignItems:"center", justifyContent:"center" },
  typeBadgeText:   { fontSize:12 },
  // Type selection
  typeRow:         { gap:12 },
  typeCard:        { flexDirection:"row", alignItems:"flex-start", gap:12, padding:16,
                     borderRadius:theme.radius.lg, borderWidth:1.5, ...theme.shadow.sm },
  typeIcon:        { fontSize:26 },
  typeLabel:       { fontSize:theme.font.size.lg, fontWeight:"800", marginBottom:4 },
  typeTagline:     { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, lineHeight:18, marginBottom:4 },
  priceHint:       { fontSize:theme.font.size.xs, fontWeight:"700" },
  helpBox:         { backgroundColor:theme.colors.infoBg, borderRadius:theme.radius.md,
                     padding:12, borderWidth:1, borderColor:theme.colors.infoBorder },
  helpText:        { fontSize:theme.font.size.sm, color:theme.colors.infoText, lineHeight:22 },
  // Service list
  typeBanner:      { flexDirection:"row", alignItems:"center", paddingHorizontal:12, paddingVertical:8,
                     borderRadius:theme.radius.full, borderWidth:1, alignSelf:"flex-start" },
  typeBannerText:  { fontSize:theme.font.size.sm, fontWeight:"700" },
  serviceCard:     { flexDirection:"row", alignItems:"center", gap:12, padding:14,
                     backgroundColor:theme.colors.surface, borderRadius:theme.radius.lg,
                     borderWidth:1, borderColor:theme.colors.border, ...theme.shadow.sm },
  serviceIcon:     { fontSize:26, width:34 },
  serviceName:     { fontSize:theme.font.size.base, fontWeight:"700", color:theme.colors.textPrimary, marginBottom:3 },
  serviceDesc:     { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, lineHeight:18, marginBottom:4 },
  serviceCategory: { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, marginTop:2 },
  duration:        { fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
  checklistPreview:{ fontSize:theme.font.size.xs, color:theme.colors.textTertiary, marginTop:4, fontStyle:"italic" },
  pill:            { paddingHorizontal:8, paddingVertical:3, borderRadius:99, backgroundColor:theme.colors.dangerBg },
  pillTxt:         { fontSize:theme.font.size.xs, fontWeight:"700" },
  // Schedule / summary
  summary:         { padding:16, borderRadius:theme.radius.lg, borderWidth:1.5, gap:12, ...theme.shadow.sm },
  summaryTitle:    { fontSize:theme.font.size.lg, fontWeight:"700" },
  summaryCategory: { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, marginTop:2 },
  priceBox:        { padding:12, borderRadius:theme.radius.md, backgroundColor:theme.colors.dangerBg,
                     borderWidth:1, borderColor:theme.colors.dangerBorder, marginTop:4 },
  priceBoxTitle:   { fontSize:theme.font.size.sm, fontWeight:"800", color:theme.colors.dangerText, marginBottom:6 },
  priceBoxLine:    { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, lineHeight:21 },
  fieldLabel:      { fontSize:theme.font.size.sm, fontWeight:"600", color:theme.colors.textSecondary, marginBottom:6 },
  input:           { height:44, borderWidth:1, borderColor:theme.colors.border, borderRadius:theme.radius.md,
                     paddingHorizontal:12, fontSize:theme.font.size.base, color:theme.colors.textPrimary,
                     backgroundColor:theme.colors.surfaceSunken },
  chip:            { paddingHorizontal:12, paddingVertical:8, borderRadius:theme.radius.full,
                     borderWidth:1, borderColor:theme.colors.border, backgroundColor:theme.colors.surfaceSunken },
  chipText:        { fontSize:theme.font.size.sm, fontWeight:"600", color:theme.colors.textSecondary },
});

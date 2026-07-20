import React from "react";
import { ScrollView, StyleSheet, Text } from "react-native";
import { theme, gs } from "../../styles/theme";
import { CustomerContactCard } from "../../components/ux05/CustomerContactCard";
import { AddressCard } from "../../components/ux05/AddressCard";
import { PermissionRestrictedState } from "../../components/ux05/PermissionRestrictedState";
import { NotificationCard } from "../../components/ux05/NotificationCard";

// Long real-length Hindi and Punjabi sentences (not lorem ipsum) -- picked
// to be realistically longer than the English placeholder text these
// components ship with by default, to spot-check wrapping/truncation.
const LONG_HINDI = "ग्राहक ने बताया कि एयर कंडीशनर ठंडी हवा नहीं दे रहा है और कंप्रेसर से अजीब सी आवाज़ आ रही है, कृपया जल्द से जल्द तकनीशियन भेजें और सर्विस पूरी होने के बाद रसीद भी उपलब्ध कराएं।";
const LONG_PUNJABI = "ਗਾਹਕ ਨੇ ਦੱਸਿਆ ਕਿ ਏਅਰ ਕੰਡੀਸ਼ਨਰ ਠੰਡੀ ਹਵਾ ਨਹੀਂ ਦੇ ਰਿਹਾ ਅਤੇ ਕੰਪ੍ਰੈਸਰ ਤੋਂ ਅਜੀਬ ਆਵਾਜ਼ ਆ ਰਹੀ ਹੈ, ਕਿਰਪਾ ਕਰਕੇ ਜਲਦੀ ਤਕਨੀਸ਼ੀਅਨ ਭੇਜੋ।";

/**
 * Dev-only localization spot-check (workstream 31). No i18n infrastructure
 * was built (no string-catalog/translation-loading mechanism exists in this
 * app) -- this only verifies that REAL long Hindi/Punjabi strings, dropped
 * directly into a handful of already-built components, don't visibly break
 * layout. See localization-readiness-report.md for what was actually
 * checked and the honest scope of "spot-check" vs. real i18n.
 */
export function LocalizationShowcaseScreen() {
  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content} testID="localization-showcase">
      <Text style={gs.label}>Hindi -- Customer Contact (issueSummary)</Text>
      <CustomerContactCard contact={{
        meta:{readiness:"mock_design_only"}, name:"राजेश कुमार", city:"नई दिल्ली", zipcode:"110001",
        issueSummary: LONG_HINDI, preferredDate:null, preferredTimeWindow:null,
        callSupported:false, messageSupported:true,
      }} />

      <Text style={gs.label}>Punjabi -- Address Card</Text>
      <AddressCard contact={{
        meta:{readiness:"mock_design_only"}, name:"ਹਰਪ੍ਰੀਤ ਸਿੰਘ", city:"ਲੁਧਿਆਣਾ, ਪੰਜਾਬ", zipcode:"141001",
        issueSummary:null, preferredDate:null, preferredTimeWindow:null,
        callSupported:false, messageSupported:false,
      }} />

      <Text style={gs.label}>Hindi -- Restricted state reason</Text>
      <PermissionRestrictedState reason={LONG_HINDI} />

      <Text style={gs.label}>Punjabi -- Notification (body truncates at 2 lines by design)</Text>
      <NotificationCard onPress={() => {}} item={{
        meta:{readiness:"mock_design_only"}, priority:"medium",
        notification: {
          id:"n1", notification_type:"job_update", title:"ਨਵੀਂ ਨੌਕਰੀ ਨਿਰਧਾਰਤ", body: LONG_PUNJABI,
          action_url:null, action_label:null, source_record_type:null, source_record_id:null,
          severity:"info", read_status:"unread", read_at:null, created_at:new Date().toISOString(),
        },
      }} />
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content: { padding:theme.spacing.base, gap:8, paddingBottom:32 },
});

import React, { useEffect, useState } from "react";
import { Image, Modal, Pressable, ScrollView, View } from "react-native";

import { useSubmitGlobalServiceLeadMutation } from "../../api/globalServices/useSubmitGlobalServiceLeadMutation";
import { useTheme } from "../../design-system/theme";
import { GlobalService } from "../../domain/globalServices";
import { AppButton, AppInput, AppText, Icon } from "../index";


const DIGITAL_STUDIO_IMAGE = require("../../../assets/fuvay-digital-studio.png");
const PHONE_PATTERN = /^\d{10}$/;

export interface GlobalServiceInquiryModalProps {
  service: GlobalService | null;
  defaultZipcode?: string | null;
  onClose: () => void;
}

export function GlobalServiceInquiryModal({ service, defaultZipcode, onClose }: GlobalServiceInquiryModalProps) {
  const { theme } = useTheme();
  const mutation = useSubmitGlobalServiceLeadMutation();
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [zipcode, setZipcode] = useState(defaultZipcode ?? "");
  const [message, setMessage] = useState("");
  const [phoneError, setPhoneError] = useState<string>();
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    if (!service) return;
    setName("");
    setPhone("");
    setEmail("");
    setZipcode(defaultZipcode ?? "");
    setMessage("");
    setPhoneError(undefined);
    setSubmitted(false);
    mutation.reset();
    // Reset only when a new service is chosen.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [service?.id]);

  function submit() {
    if (!service || !name.trim()) return;
    if (!PHONE_PATTERN.test(phone)) {
      setPhoneError("Enter a valid 10-digit phone number");
      return;
    }
    mutation.mutate(
      {
        globalServiceId: service.id,
        name: name.trim(),
        phone,
        email: email.trim(),
        zipcode: zipcode.trim(),
        message: message.trim(),
      },
      { onSuccess: () => setSubmitted(true) },
    );
  }

  return (
    <Modal visible={!!service} animationType="slide" transparent onRequestClose={onClose}>
      <View style={{ flex: 1, justifyContent: "flex-end", backgroundColor: theme.colors.backgroundOverlay }}>
        <View
          style={{
            maxHeight: "92%",
            backgroundColor: theme.colors.surfaceDefault,
            borderTopLeftRadius: theme.radius.radiusLarge,
            borderTopRightRadius: theme.radius.radiusLarge,
            overflow: "hidden",
          }}
        >
          <View style={{ height: 128 }}>
            <Image source={DIGITAL_STUDIO_IMAGE} resizeMode="cover" style={{ width: "100%", height: "100%" }} />
            <View style={{ position: "absolute", top: 0, right: 0, bottom: 0, left: 0, backgroundColor: theme.colors.campaignScrim }} />
            <View style={{ position: "absolute", left: theme.spacing.base, right: theme.spacing.base, top: theme.spacing.base, flexDirection: "row", alignItems: "flex-start" }}>
              <View style={{ flex: 1, paddingRight: theme.spacing.md }}>
                <AppText variant="caption" color="inverse" style={{ opacity: 0.82, fontWeight: "700" }}>FUVAY DIGITAL STUDIO</AppText>
                <AppText variant="headingSmall" color="inverse" accessibilityRole="header" style={{ marginTop: 4 }}>
                  {service?.name ?? "Start a project"}
                </AppText>
              </View>
              <Pressable
                onPress={onClose}
                accessibilityRole="button"
                accessibilityLabel="Close"
                style={({ pressed }) => ({ width: 44, height: 44, alignItems: "center", justifyContent: "center", backgroundColor: theme.material.highlight, opacity: pressed ? theme.opacity.pressed : 1 })}
              >
                <Icon name="close" color={theme.colors.brandOnPrimary} decorative />
              </Pressable>
            </View>
          </View>

          {submitted ? (
            <View style={{ padding: theme.spacing.xl, alignItems: "center" }}>
              <Icon name="checkmark-circle" size="feature" color={theme.colors.statusSuccess} decorative />
              <AppText variant="headingSmall" align="center" style={{ marginTop: theme.spacing.base }}>Your project brief is in</AppText>
              <AppText variant="bodySmall" color="secondary" align="center" style={{ marginTop: theme.spacing.xs }}>
                A Fuvay product specialist will contact you to discuss scope, timeline and next steps.
              </AppText>
              <View style={{ width: "100%", marginTop: theme.spacing.lg }}>
                <AppButton label="Done" onPress={onClose} fullWidth />
              </View>
            </View>
          ) : (
            <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ padding: theme.spacing.base, paddingBottom: theme.spacing.xl }}>
              <AppText variant="bodySmall" color="secondary" style={{ marginBottom: theme.spacing.base }}>
                {service?.tagline ?? "Tell us what you want to build. This creates a callback request, not a home-service booking."}
              </AppText>
              <AppInput label="Your name" accessibilityLabel="Your name" value={name} onChangeText={setName} placeholder="Full name" />
              <View style={{ marginTop: theme.spacing.sm }}>
                <AppInput
                  label="Phone number"
                  accessibilityLabel="Phone number"
                  value={phone}
                  onChangeText={value => {
                    setPhone(value.replace(/\D/g, "").slice(0, 10));
                    setPhoneError(undefined);
                  }}
                  keyboardType="number-pad"
                  maxLength={10}
                  error={phoneError}
                  placeholder="9876543210"
                />
              </View>
              <View style={{ marginTop: theme.spacing.sm }}>
                <AppInput label="Email (optional)" accessibilityLabel="Email" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" placeholder="you@company.com" />
              </View>
              <View style={{ marginTop: theme.spacing.sm }}>
                <AppInput label="PIN code (optional)" accessibilityLabel="PIN code" value={zipcode} onChangeText={value => setZipcode(value.replace(/\D/g, "").slice(0, 6))} keyboardType="number-pad" maxLength={6} placeholder="140412" />
              </View>
              <View style={{ marginTop: theme.spacing.sm }}>
                <AppInput label="What do you want to build? (optional)" accessibilityLabel="Project brief" value={message} onChangeText={setMessage} multiline numberOfLines={3} placeholder="Share your idea, business goal or current challenge" />
              </View>
              {mutation.isError ? <AppText variant="bodySmall" color="danger" style={{ marginTop: theme.spacing.sm }}>We could not send your request. Please try again.</AppText> : null}
              <View style={{ marginTop: theme.spacing.base }}>
                <AppButton label={mutation.isPending ? "Sending…" : "Request a project call"} onPress={submit} disabled={mutation.isPending || !name.trim() || phone.length !== 10} fullWidth />
              </View>
            </ScrollView>
          )}
        </View>
      </View>
    </Modal>
  );
}

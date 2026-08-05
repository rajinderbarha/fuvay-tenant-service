import React, { useEffect, useState } from "react";
import { Modal, View, ScrollView } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText, AppButton, AppInput, AppIconButton } from "../index";
import { Icon } from "../Icon";
import { GlobalService } from "../../domain/globalServices";
import { useSubmitGlobalServiceLeadMutation } from "../../api/globalServices/useSubmitGlobalServiceLeadMutation";

export interface GlobalServiceInquiryModalProps {
  service: GlobalService | null;
  defaultName?: string;
  defaultZipcode?: string | null;
  onClose: () => void;
}

const PHONE_PATTERN = /^\d{10}$/;

/**
 * Collects the fixed, small set of fields the backend requires
 * (name/phone required; email/zipcode/message optional) and submits
 * POST /v1/customer/global-services/leads. No booking is created -- on
 * success this shows a "we'll call you" confirmation, not a booking
 * summary, since there is no booking.
 */
export function GlobalServiceInquiryModal({ service, defaultName, defaultZipcode, onClose }: GlobalServiceInquiryModalProps) {
  const { theme } = useTheme();
  const submitLead = useSubmitGlobalServiceLeadMutation();
  const [name, setName] = useState(defaultName ?? "");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [zipcode, setZipcode] = useState(defaultZipcode ?? "");
  const [message, setMessage] = useState("");
  const [phoneError, setPhoneError] = useState<string | undefined>();
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    if (service) {
      setName(defaultName ?? "");
      setPhone("");
      setEmail("");
      setZipcode(defaultZipcode ?? "");
      setMessage("");
      setPhoneError(undefined);
      setSubmitted(false);
      submitLead.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [service?.id]);

  function handleSubmit() {
    if (!service) return;
    if (!name.trim()) return;
    if (!PHONE_PATTERN.test(phone)) {
      setPhoneError("Enter a valid 10-digit phone number");
      return;
    }
    submitLead.mutate(
      { globalServiceId: service.id, name: name.trim(), phone, email: email.trim(), zipcode: zipcode.trim(), message: message.trim() },
      { onSuccess: () => setSubmitted(true) },
    );
  }

  return (
    <Modal visible={!!service} animationType="slide" transparent onRequestClose={onClose}>
      <View style={{ flex: 1, justifyContent: "flex-end", backgroundColor: theme.colors.backgroundOverlay }}>
        <View
          style={{
            backgroundColor: theme.colors.surfaceDefault, borderTopLeftRadius: theme.radiusUsage.card,
            borderTopRightRadius: theme.radiusUsage.card, padding: theme.spacing.base, maxHeight: "88%",
          }}
        >
          <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: theme.spacing.base }}>
            <AppText variant="headingSmall" accessibilityRole="header">{service?.name ?? ""}</AppText>
            <AppIconButton name="close" accessibilityLabel="Close" onPress={onClose} />
          </View>

          {submitted ? (
            <View style={{ alignItems: "center", paddingVertical: theme.spacing.xl }}>
              <Icon name="checkmark-circle" size="feature" color={theme.colors.statusSuccess} decorative />
              <AppText variant="headingSmall" style={{ marginTop: theme.spacing.base, textAlign: "center" }}>
                We&apos;ve got your request
              </AppText>
              <AppText variant="bodySmall" color="secondary" style={{ marginTop: theme.spacing.xs, textAlign: "center" }}>
                Our team will call you shortly to discuss {service?.name.toLowerCase()}.
              </AppText>
              <View style={{ marginTop: theme.spacing.lg, width: "100%" }}>
                <AppButton label="Done" onPress={onClose} fullWidth />
              </View>
            </View>
          ) : (
            <ScrollView keyboardShouldPersistTaps="handled">
              {service?.tagline ? (
                <AppText variant="bodySmall" color="secondary" style={{ marginBottom: theme.spacing.base }}>{service.tagline}</AppText>
              ) : null}
              <AppInput label="Your name" accessibilityLabel="Your name" value={name} onChangeText={setName} placeholder="Full name" />
              <View style={{ marginTop: theme.spacing.sm }}>
                <AppInput
                  label="Phone number" accessibilityLabel="Phone number" value={phone}
                  onChangeText={t => { setPhone(t.replace(/\D/g, "").slice(0, 10)); setPhoneError(undefined); }}
                  keyboardType="number-pad" maxLength={10} error={phoneError} placeholder="9876543210"
                />
              </View>
              <View style={{ marginTop: theme.spacing.sm }}>
                <AppInput label="Zipcode (optional)" accessibilityLabel="Zipcode" value={zipcode}
                  onChangeText={t => setZipcode(t.replace(/\D/g, "").slice(0, 6))} keyboardType="number-pad" maxLength={6} placeholder="141001" />
              </View>
              <View style={{ marginTop: theme.spacing.sm }}>
                <AppInput label="What do you need? (optional)" accessibilityLabel="Message" value={message}
                  onChangeText={setMessage} placeholder="Tell us a bit about your requirement" multiline numberOfLines={3} />
              </View>
              {submitLead.isError ? (
                <AppText variant="bodySmall" color="danger" style={{ marginTop: theme.spacing.sm }}>
                  Something went wrong. Please try again.
                </AppText>
              ) : null}
              <View style={{ marginTop: theme.spacing.base }}>
                <AppButton
                  label={submitLead.isPending ? "Sending…" : "Request a callback"}
                  onPress={handleSubmit}
                  disabled={submitLead.isPending || !name.trim() || phone.length !== 10}
                  fullWidth
                />
              </View>
            </ScrollView>
          )}
        </View>
      </View>
    </Modal>
  );
}

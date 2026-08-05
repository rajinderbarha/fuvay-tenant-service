import React, { useState } from "react";
import { View, Alert } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { LoadingState } from "../../components/LoadingState";
import { PersonalDetailsHeader } from "../../components/personal-details/PersonalDetailsHeader";
import { AvatarEditor } from "../../components/personal-details/AvatarEditor";
import { BasicInformationForm } from "../../components/personal-details/BasicInformationForm";
import { ContactInformationCard } from "../../components/personal-details/ContactInformationCard";
import { SaveProfilePanel } from "../../components/personal-details/SaveProfilePanel";
import { useCustomerProfileQuery } from "../../api/customer/useCustomerProfileQuery";
import { useUpdateCustomerProfileMutation } from "../../api/customer/useUpdateCustomerProfileMutation";
import { validateFullName, normalizeFullName } from "../../domain/profileValidation";
import { maskPhoneForDisplay } from "../../domain/phone";
import { DomainError } from "../../domain/errors";

/**
 * Personal Details (spec: opened from Profile -> "Edit profile"). Only
 * `full_name` is editable -- the sole field this screen's approved design
 * surfaces and the backend proves mutable (spec section 3: "If only the
 * customer name can currently be updated, implement only name editing").
 * Mobile/email render as read-only verified rows: no complete OTP
 * contact-change flow was found this task (confirmed via direct audit of
 * `app/engines/auth/router.py` -- only LOGIN phone OTP exists, no
 * authenticated contact-change OTP endpoint), so `Change` is never shown
 * (spec section 5: "hide Change and keep the row read-only"). Avatar
 * upload is similarly absent -- no confirmed upload contract.
 */
export function EditProfileScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation();
  const query = useCustomerProfileQuery();
  const mutation = useUpdateCustomerProfileMutation();

  const serverFullName = query.data?.fullName ?? "";
  const [fullName, setFullName] = useState(serverFullName);
  const [touched, setTouched] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  if (!query.data) {
    return (
      <AppScreen>
        <LoadingState label="Loading" />
      </AppScreen>
    );
  }

  const profile = query.data;
  const dirty = touched && normalizeFullName(fullName) !== normalizeFullName(serverFullName);
  const validation = validateFullName(fullName);
  const fieldError = touched && !validation.valid ? validation.error : null;

  function confirmDiscard(onDiscard: () => void) {
    if (!dirty) {
      onDiscard();
      return;
    }
    Alert.alert("Discard changes?", "Your unsaved profile changes will be lost.", [
      { text: "Keep editing", style: "cancel" },
      { text: "Discard", style: "destructive", onPress: onDiscard },
    ]);
  }

  function handleDiscard() {
    setFullName(serverFullName);
    setTouched(false);
    setServerError(null);
  }

  async function handleSave() {
    setServerError(null);
    const check = validateFullName(fullName);
    if (!check.valid) {
      setTouched(true);
      return;
    }
    try {
      await mutation.mutateAsync({ full_name: normalizeFullName(fullName) });
      navigation.goBack();
    } catch (err) {
      // Preserve entered value on recoverable failure (spec section 9) --
      // never resets `fullName` here.
      setServerError(err instanceof DomainError ? err.diagnostic : "Couldn't save your changes. Please try again.");
    }
  }

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      <View style={{ gap: theme.spacing.base }}>
        <PersonalDetailsHeader
          onBack={() => confirmDiscard(() => navigation.goBack())}
          onCancel={() => confirmDiscard(() => navigation.goBack())}
        />

        <AvatarEditor
          name={profile.displayName ?? profile.fullName ?? "Your account"}
          avatarUrl={profile.avatarUrl}
          canUpdateAvatar={profile.capabilities.canUpdateAvatar}
        />

        <BasicInformationForm
          fullName={fullName}
          onChangeFullName={t => { setFullName(t); setTouched(true); }}
          error={fieldError}
        />

        <ContactInformationCard
          maskedPhone={profile.phone ? maskPhoneForDisplay(profile.phone) : null}
          email={profile.email}
          verified={profile.verified}
        />

        {serverError ? <AppText variant="bodySmall" color="danger">{serverError}</AppText> : null}

        <SaveProfilePanel
          dirty={dirty}
          saving={mutation.isPending}
          canSave={validation.valid}
          onDiscard={() => confirmDiscard(handleDiscard)}
          onSave={handleSave}
        />
      </View>
    </AppScreen>
  );
}

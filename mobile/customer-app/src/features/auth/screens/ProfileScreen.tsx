import React, { useState } from "react";
import { useNavigation } from "@react-navigation/native";
import { ScreenContainer } from "../../../components/layout/ScreenContainer";
import { Stack } from "../../../components/layout/Stack";
import { Section } from "../../../components/layout/Section";
import { AppText } from "../../../components/primitives/AppText";
import { AppButton } from "../../../components/primitives/AppButton";
import { AppTextField } from "../../../components/forms/AppTextField";
import { AppAvatar } from "../../../components/primitives/AppAvatar";
import { useAuthSession } from "../hooks/use-auth-session";
import { useUpdateProfile } from "../queries/profile-queries";
import { useLogout } from "../hooks/use-logout";
import { customerInitials } from "../domain/session";

export function ProfileScreen() {
  const navigation = useNavigation<any>();
  const { session } = useAuthSession();
  const updateProfile = useUpdateProfile();
  const { logout, loading: loggingOut } = useLogout();
  const [fullName, setFullName] = useState(session?.fullName ?? "");

  if (!session) {
    return (
      <ScreenContainer scrollable={false}>
        <AppText variant="bodyMedium" color="textSecondary" align="center">
          Sign in to see your profile.
        </AppText>
      </ScreenContainer>
    );
  }

  return (
    <ScreenContainer>
      <Stack gap={7}>
        <Stack gap={3} align="center">
          <AppAvatar accessibilityLabel="Your profile photo" imageUrl={session.avatarUrl} initials={customerInitials(session)} size="lg" />
          <AppText variant="headingMedium">{session.fullName}</AppText>
        </Stack>

        <Section title="Account">
          <AppTextField label="Full name" value={fullName} onChangeText={setFullName} required />
          <AppText variant="labelMedium" color="textSecondary">
            Phone: {session.phone ?? "Not set"}
          </AppText>
          <AppButton
            label={updateProfile.isPending ? "Saving…" : "Save changes"}
            onPress={() => updateProfile.mutate({ full_name: fullName })}
            variant="primary"
            size="medium"
            loading={updateProfile.isPending}
            disabled={fullName.trim().length < 2}
          />
        </Section>

        <Section title="Security">
          <AppButton label="Sessions and devices" onPress={() => navigation.navigate("Sessions")} variant="secondary" size="medium" />
        </Section>

        <AppButton label="Sign out" onPress={logout} variant="destructive" size="medium" loading={loggingOut} />
      </Stack>
    </ScreenContainer>
  );
}

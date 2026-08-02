import React, { useState } from "react";
import { View, ScrollView } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { TextField } from "../../design-system/components/forms/TextField";
import { PrimaryButton, SecondaryButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { useProfile } from "./useProfile";
import { ScreenHeader } from "./components/ScreenHeader";
import * as authApi from "../../services/auth/authApi";
import { uploadProfilePhoto } from "../../services/media/mediaApi";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "EditPersonalProfile">;

/**
 * Edit Personal Profile (Phase R spec section 4). Only technician-editable
 * fields (display name, photo) are here -- everything tenant/platform-
 * controlled (business, role, designation, verification) lives on the
 * read-only Employment Details screen instead.
 */
export function EditPersonalProfileScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const { data, isLoading, refetch } = useProfile();
  const [fullName, setFullName] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);

  const nameValue = fullName ?? data?.identity.full_name ?? "";

  const handlePickPhoto = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) return;
    const result = await ImagePicker.launchImageLibraryAsync({ quality: 0.7, allowsEditing: true, aspect: [1, 1] });
    if (result.canceled || !result.assets?.[0]) return;
    const asset = result.assets[0];
    setUploadingPhoto(true);
    setError(null);
    const upload = await uploadProfilePhoto(asset.uri, asset.fileName ?? "photo.jpg", asset.mimeType ?? "image/jpeg");
    if (upload.ok) await refetch();
    else setError(upload.error.safeMessage);
    setUploadingPhoto(false);
  };

  const handleSave = async () => {
    if (!nameValue.trim()) return;
    setBusy(true);
    setError(null);
    const result = await authApi.updateMyProfile({ fullName: nameValue.trim() });
    setBusy(false);
    if (result.ok) { await refetch(); navigation.goBack(); }
    else setError(result.error.safeMessage);
  };

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Edit profile" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        {error ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="danger" title="Couldn't save" message={error} /></View> : null}
        <Section>
          <Card>
            <AppText variant="bodyStrong">Photo</AppText>
            <SecondaryButton label="Change photo" onPress={handlePickPhoto} loading={uploadingPhoto} style={{ marginTop: theme.spacing.sm }} />
          </Card>
        </Section>
        <Section>
          <Card>
            <TextField label="Display name" value={nameValue} onChangeText={setFullName} editable={!isLoading} />
          </Card>
        </Section>
        <PrimaryButton label="Save" onPress={handleSave} loading={busy} disabled={!nameValue.trim()} fullWidth />
      </ScrollView>
    </SafeAreaScreen>
  );
}

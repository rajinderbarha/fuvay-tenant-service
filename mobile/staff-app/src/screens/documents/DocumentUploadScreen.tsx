import React, { useState } from "react";
import { View, ScrollView } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { TextField } from "../../design-system/components/forms/TextField";
import { Checkbox } from "../../design-system/components/forms/Checkbox";
import { PrimaryButton, SecondaryButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { useDocuments } from "./useDocuments";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";

type Props = NativeStackScreenProps<ProfileStackParamList, "DocumentUpload">;

/** Guided upload flow (spec section 7). Mark-successful only after the
 * backend accepts the submission (never just because bytes reached
 * storage) -- useDocuments().submit awaits both the upload AND the
 * document-submit call before resolving ok. */
export function DocumentUploadScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const initialCode = route.params?.docCode;
  const { data, submit, uploading, uploadError } = useDocuments();
  const networkStatus = useNetworkStatus();
  const offline = networkStatus === "offline" || networkStatus === "internet_reachable_false";

  const [docCode, setDocCode] = useState<string | undefined>(initialCode);
  const [pickedAsset, setPickedAsset] = useState<ImagePicker.ImagePickerAsset | null>(null);
  const [documentNumber, setDocumentNumber] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [done, setDone] = useState(false);

  const requirement = data?.requirements.find(r => r.code === docCode);
  const pickableRequirements = data?.requirements ?? [];

  const handlePick = async (fromCamera: boolean) => {
    const permission = fromCamera
      ? await ImagePicker.requestCameraPermissionsAsync()
      : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) return;
    const result = fromCamera
      ? await ImagePicker.launchCameraAsync({ quality: 0.8 })
      : await ImagePicker.launchImageLibraryAsync({ quality: 0.8 });
    if (result.canceled || !result.assets?.[0]) return;
    setPickedAsset(result.assets[0]);
  };

  const canSubmit = !!docCode && !!pickedAsset && confirmed && !offline && (!requirement?.requires_expiry || !!expiryDate);

  const handleSubmit = async () => {
    if (!canSubmit || !docCode || !pickedAsset) return;
    const result = await submit(
      docCode, pickedAsset.uri, pickedAsset.fileName ?? "document.jpg", pickedAsset.mimeType ?? "image/jpeg",
      {
        documentNumber: documentNumber.trim() || undefined,
        expiryDate: expiryDate.trim() || undefined,
      },
    );
    if (result.ok) setDone(true);
  };

  if (done) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Upload document" onBack={() => navigation.goBack()} />
        <View style={{ padding: theme.spacing.lg }}>
          <InlineAlert tone="success" title="Submitted for review" message="Your document was submitted and is now under review by your business." />
          <View style={{ height: theme.spacing.base }} />
          <PrimaryButton label="Done" onPress={() => navigation.goBack()} fullWidth />
        </View>
      </SafeAreaScreen>
    );
  }

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Upload document" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        {offline ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="neutral" title="Offline" message="A secure connection is required to upload documents." /></View> : null}

        {!docCode ? (
          <Section>
            <AppText variant="bodyStrong" style={{ marginBottom: theme.spacing.sm }}>Which document?</AppText>
            {pickableRequirements.map(r => (
              <SecondaryButton key={r.requirement_id} label={r.label} onPress={() => setDocCode(r.code)} style={{ marginBottom: theme.spacing.xs }} />
            ))}
          </Section>
        ) : (
          <>
            <Section>
              <Card>
                <AppText variant="bodyStrong">{requirement?.label ?? docCode}</AppText>
                <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.xs }}>
                  Allowed formats: PDF, JPEG, PNG · Max size: 10MB{requirement?.requires_expiry ? " · Expiry date required" : ""}
                </AppText>
                <AppText variant="caption" color="tertiary">Reviewed only by your business's authorized reviewers.</AppText>
              </Card>
            </Section>

            <Section>
              <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
                <SecondaryButton label="Take photo" onPress={() => handlePick(true)} />
                <SecondaryButton label="Choose file" onPress={() => handlePick(false)} />
              </View>
              {pickedAsset ? <AppText variant="bodySmall" color="success" style={{ marginTop: theme.spacing.sm }}>File selected</AppText> : null}
            </Section>

            <Section>
              <TextField label="Document number (optional)" value={documentNumber} onChangeText={setDocumentNumber} />
              {requirement?.requires_expiry ? (
                <View style={{ marginTop: theme.spacing.sm }}>
                  <TextField label="Expiry date (YYYY-MM-DD)" value={expiryDate} onChangeText={setExpiryDate} placeholder="2026-12-31" required />
                </View>
              ) : null}
            </Section>

            <Section>
              <Checkbox
                label="I confirm this document is accurate and belongs to me"
                checked={confirmed}
                onChange={setConfirmed}
              />
            </Section>

            {uploadError ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="danger" title="Couldn't submit" message={uploadError.safeMessage} /></View> : null}

            <PrimaryButton label="Submit for review" onPress={handleSubmit} loading={uploading} disabled={!canSubmit} fullWidth />
          </>
        )}
      </ScrollView>
    </SafeAreaScreen>
  );
}

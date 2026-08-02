import React from "react";
import { View } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { AppText } from "../../../design-system/components/typography/AppText";
import { AttachmentThumbnail } from "../../../design-system/components/data-display/AttachmentThumbnail";
import { LoadingSpinner } from "../../../design-system/components/feedback/Loading";

export interface EvidenceGridProps {
  beforeIds: string[];
  afterIds: string[];
  editable: boolean;
  uploadingCategory: "before" | "after" | null;
  onAddBefore: () => void;
  onAddAfter: () => void;
  onRemove: (category: "before" | "after", fileId: string) => void;
}

/** Before/after are always visually distinguished by an explicit label, not
 * color alone (spec section 20). "Before" photos are technician-tagged in
 * this phase -- automatic carryover from inspection evidence was not built
 * (disclosed deviation). */
export function EvidenceGrid({ beforeIds, afterIds, editable, uploadingCategory, onAddBefore, onAddAfter, onRemove }: EvidenceGridProps) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.sm }}>
      {beforeIds.map(id => (
        <AttachmentThumbnail key={`before-${id}`} label="Before" onPress={editable ? () => onRemove("before", id) : undefined} />
      ))}
      {afterIds.map(id => (
        <AttachmentThumbnail key={`after-${id}`} label="After" onPress={editable ? () => onRemove("after", id) : undefined} />
      ))}
      {editable ? (
        uploadingCategory ? (
          <LoadingSpinner />
        ) : (
          <AttachmentThumbnail label="Add photo" onPress={onAddAfter} />
        )
      ) : null}
      {beforeIds.length === 0 && afterIds.length === 0 && !editable ? (
        <AppText variant="bodySmall" color="tertiary">No evidence captured.</AppText>
      ) : null}
    </View>
  );
}

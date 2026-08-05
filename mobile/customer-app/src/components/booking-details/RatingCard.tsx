import React, { useState } from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppButton } from "../AppButton";
import { AppInput } from "../AppInput";
import { Icon } from "../Icon";
import { CustomerReview, REVIEW_TAG_OPTIONS } from "../../domain/customerReview";

export interface RatingCardProps {
  existingReview: CustomerReview | null;
  onSubmit: (rating: number, tags: string[], comment: string) => void;
  submitting: boolean;
}

/** "How was your service?" -- only rendered once a job is genuinely
 * `completed` (the real backend eligibility gate, `REVIEW_NOT_ELIGIBLE`,
 * would reject a submission otherwise; the caller only mounts this once
 * `completion` is proven non-null). Once `existingReview` is present, this
 * renders the submitted review read-only -- never re-opens the form
 * (`REVIEW_ALREADY_SUBMITTED` is the real backend's own one-review rule). */
export function RatingCard({ existingReview, onSubmit, submitting }: RatingCardProps) {
  const { theme } = useTheme();
  const [rating, setRating] = useState(0);
  const [tags, setTags] = useState<string[]>([]);
  const [comment, setComment] = useState("");

  if (existingReview) {
    return (
      <AppCard>
        <AppText variant="labelStrong" color="secondary">Your review</AppText>
        <View style={{ flexDirection: "row", marginTop: theme.spacing.xxs }} accessibilityLabel={`You rated this service ${existingReview.rating} out of 5 stars`}>
          {[1, 2, 3, 4, 5].map(n => (
            <Icon
              key={n} name={n <= existingReview.rating ? "star" : "star-outline"} size="standard"
              color={n <= existingReview.rating ? theme.colors.brandPrimary : theme.colors.borderDefault} decorative
            />
          ))}
        </View>
        {existingReview.comment ? <AppText variant="body" style={{ marginTop: theme.spacing.xs }}>{existingReview.comment}</AppText> : null}
      </AppCard>
    );
  }

  function toggleTag(value: string) {
    setTags(prev => prev.includes(value) ? prev.filter(t => t !== value) : [...prev, value]);
  }

  return (
    <AppCard>
      <AppText variant="labelStrong" color="secondary">How was your service?</AppText>
      <View style={{ flexDirection: "row", gap: theme.spacing.xs, marginTop: theme.spacing.xs }}>
        {[1, 2, 3, 4, 5].map(n => (
          <Pressable
            key={n} onPress={() => setRating(n)} hitSlop={8}
            accessibilityRole="button" accessibilityLabel={`Rate ${n} out of 5 stars`}
            accessibilityState={{ selected: n <= rating }}
            style={{ minWidth: 44, minHeight: 44, alignItems: "center", justifyContent: "center" }}
          >
            <Icon name={n <= rating ? "star" : "star-outline"} size="feature" color={theme.colors.brandPrimaryStrong} decorative />
          </Pressable>
        ))}
      </View>

      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.xs, marginTop: theme.spacing.sm }}>
        {REVIEW_TAG_OPTIONS.map(opt => {
          const selected = tags.includes(opt.value);
          return (
            <Pressable
              key={opt.value} onPress={() => toggleTag(opt.value)}
              accessibilityRole="button" accessibilityLabel={opt.label} accessibilityState={{ selected }}
              style={{
                minHeight: 44, paddingHorizontal: theme.spacing.sm, borderRadius: theme.radius.radiusFull,
                borderWidth: 1, borderColor: selected ? theme.colors.brandPrimary : theme.colors.borderDefault,
                backgroundColor: selected ? theme.colors.brandPrimaryMuted : "transparent",
                alignItems: "center", justifyContent: "center",
              }}
            >
              <AppText variant="labelStrong" style={{ color: selected ? theme.colors.brandPrimary : undefined }}>{opt.label}</AppText>
            </Pressable>
          );
        })}
      </View>

      <View style={{ marginTop: theme.spacing.sm }}>
        <AppInput label="Add a note (optional)" value={comment} onChangeText={setComment} multiline placeholder="Add a note (optional)" />
      </View>

      <AppButton
        label={submitting ? "Submitting your review…" : "Submit review"} tone="primary" fullWidth
        disabled={submitting || rating === 0} style={{ marginTop: theme.spacing.sm }}
        onPress={() => onSubmit(rating, tags, comment.trim())}
      />
    </AppCard>
  );
}

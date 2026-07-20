import React, { useState } from "react";
import { View, ScrollView } from "react-native";
import { useNavigation, useRoute, type RouteProp } from "@react-navigation/native";
import { useTranslation } from "react-i18next";
import { SafeAreaView } from "react-native-safe-area-context";
import { AppText } from "../../../components/primitives/AppText";
import { AppButton } from "../../../components/primitives/AppButton";
import { AppPressable } from "../../../components/primitives/AppPressable";
import { AppIcon } from "../../../components/primitives/AppIcon";
import { Skeleton } from "../../../components/feedback/Skeleton";
import { ErrorState } from "../../../components/feedback/ErrorState";
import { ConfirmationModal } from "../../../components/feedback/ConfirmationModal";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import { useServiceDetail } from "../../service-detail/queries/service-detail-queries";
import { useBookingAssistant } from "../hooks/use-booking-assistant";
import {
  submitAnswer,
  goToPreviousStep,
  reviseAnswer,
  completeSession,
  currentStepId,
  currentQuestionType,
  canGoBack,
  assistantProgress,
  orderedAnswerHistory,
  type AnswerRecord,
} from "../domain/assistant-session";
import {
  normalizeSingleSelectAnswer,
  normalizeMultiSelectAnswer,
  normalizeShortTextAnswer,
  normalizeInformationAcknowledgement,
} from "../domain/answer-normalization";
import { resolveQuestionRenderer } from "../domain/question-renderer-registry";
import { SingleSelectRenderer } from "../components/SingleSelectRenderer";
import { MultiSelectRenderer } from "../components/MultiSelectRenderer";
import { ShortTextRenderer } from "../components/ShortTextRenderer";
import { InformationRenderer } from "../components/InformationRenderer";
import { AssistantProgress } from "../components/AssistantProgress";
import { AnswerHistory } from "../components/AnswerHistory";
import { logger } from "../../../observability/logger";
import { mapAssistantAnswersToDraftUpdate } from "../../booking-draft/domain/assistant-answer-mapping";
import type { StepId } from "../domain/assistant-steps";
import type { RootStackParamList } from "../../../navigation/route-types";

type BookingAssistantRouteProp = RouteProp<RootStackParamList, "BookingAssistant">;

const STEP_TITLE_KEY: Record<Exclude<StepId, "completion">, string> = {
  issue_type: "assistant.issueTypeTitle",
  issue_description: "assistant.issueDescriptionTitle",
  photo_boundary: "assistant.photoBoundaryTitle",
  service_type: "assistant.serviceTypeTitle",
  service_option: "assistant.serviceOptionTitle",
  brand: "assistant.brandTitle",
  customer_note: "assistant.customerNoteTitle",
};

/**
 * The real production booking assistant (CUSTOMER-L5-05). There is no
 * backend workflow/session engine — see CUSTOMER-L5-05-contract-matrix.md —
 * so this screen sequences a client-side, in-memory-only session over real,
 * category-scoped catalog data. Nothing here is persisted across app
 * restarts; CUSTOMER-L5-06 owns durable booking-draft persistence.
 */
export function BookingAssistantScreen() {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");
  const navigation = useNavigation<any>();
  const route = useRoute<BookingAssistantRouteProp>();
  const params = route.params;
  const [exitConfirmVisible, setExitConfirmVisible] = useState(false);

  const serviceId = params?.serviceId;
  const categoryId = params?.categoryId;

  const detail = useServiceDetail(categoryId ?? "", serviceId ?? "");

  const assistant = useBookingAssistant(serviceId ?? "", categoryId ?? "", {
    requiresBrand: detail.data?.required_fields.requires_brand ?? false,
    requiresType: detail.data?.required_fields.requires_type ?? false,
    requiresCustomerNotes: detail.data?.required_fields.requires_customer_notes ?? false,
    requiresPhotoUpload: detail.data?.required_fields.requires_photo_upload ?? false,
  });

  // Entry validation (CUSTOMER-L5-05 §13): route params alone are never
  // trusted — the real service is re-fetched, matching CUSTOMER-L5-04's
  // existing booking-boundary pattern.
  if (!serviceId || !categoryId) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ padding: theme.sizes.screenHorizontalPadding as number }}>
          <ErrorState title={t("service.notFound")} onContactSupport={() => navigation.goBack()} />
        </View>
      </SafeAreaView>
    );
  }

  if (detail.isLoading) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[4] }}>
          <Skeleton height={28} width="60%" />
          <Skeleton height={120} />
        </View>
      </SafeAreaView>
    );
  }

  if (detail.isError || !detail.data) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ padding: theme.sizes.screenHorizontalPadding as number }}>
          <ErrorState title={t("service.loadError")} onRetry={() => void detail.refetch()} />
        </View>
      </SafeAreaView>
    );
  }

  if (assistant.catalogsLoading || !assistant.session) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[4] }}>
          <Skeleton height={28} width="70%" />
          <Skeleton height={64} />
          <Skeleton height={64} width="80%" />
        </View>
      </SafeAreaView>
    );
  }

  if (assistant.catalogsError) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ padding: theme.sizes.screenHorizontalPadding as number }}>
          <ErrorState title={t("assistant.loadError")} onRetry={assistant.retry} />
        </View>
      </SafeAreaView>
    );
  }

  const session = assistant.session;
  const stepId = currentStepId(session);
  const hasProgress = orderedAnswerHistory(session).length > 0 || session.currentStepIndex > 0;

  function handleExitPress() {
    if (hasProgress) setExitConfirmVisible(true);
    else navigation.goBack();
  }

  function handleBackPress() {
    if (canGoBack(session)) assistant.setSession(goToPreviousStep(session));
    else handleExitPress();
  }

  function handleEditRequest(targetStepId: string) {
    assistant.setSession(reviseAnswer(session, targetStepId as StepId));
  }

  if (stepId === "completion") {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ flex: 1, padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], justifyContent: "center" }}>
          <AppIcon name="checkmark-circle" size="xl" color="iconSuccess" />
          <AppText variant="headingLarge" accessibilityRole="header">
            {t("assistant.completionTitle")}
          </AppText>
          <AppText variant="bodyMedium" color="textSecondary">
            {t("assistant.completionDescription")}
          </AppText>
          <AppButton
            label={t("assistant.completionAction")}
            onPress={() => {
              const completed = completeSession(session);
              assistant.setSession(completed);
              const history = orderedAnswerHistory(completed);
              logger.info("diagnostic_completed", { serviceId, categoryId, stepCount: history.length });
              const mapped = mapAssistantAnswersToDraftUpdate(history);
              navigation.navigate("BookingDraft", {
                serviceId,
                categoryId,
                brandId: mapped.brand_id,
                offeringTypeId: mapped.offering_type_id,
                issueSummary: mapped.issue_summary,
              });
            }}
            variant="primary"
            size="large"
            testID="assistant-complete-button"
          />
        </View>
      </SafeAreaView>
    );
  }

  const questionType = currentQuestionType(session);
  const resolvedRenderer = questionType ? resolveQuestionRenderer(questionType) : { recognized: false as const, questionType: "unknown" };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
      <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
          <AppPressable accessibilityLabel={t("assistant.back")} onPress={handleBackPress}>
            <AppIcon name="chevron-back" size="md" color="iconPrimary" />
          </AppPressable>
          <View style={{ flex: 1 }}>
            <AssistantProgress {...assistantProgress(session)} />
          </View>
          <AppPressable accessibilityLabel="Exit" onPress={handleExitPress}>
            <AppIcon name="close" size="md" color="iconSecondary" />
          </AppPressable>
        </View>

        <AnswerHistory
          answers={orderedAnswerHistory(session)}
          questionTitles={Object.fromEntries(Object.entries(STEP_TITLE_KEY).map(([id, key]) => [id, t(key)]))}
          onEdit={handleEditRequest}
        />

        {!resolvedRenderer.recognized || !stepId ? (
          <ErrorState
            title={t("assistant.unsupportedTitle")}
            description={t("assistant.unsupportedDescription")}
            onContactSupport={() => navigation.goBack()}
          />
        ) : (
          <StepQuestion
            stepId={stepId}
            categoryId={categoryId}
            assistant={assistant}
            onSubmit={(record, branchIssueType) => assistant.setSession(submitAnswer(session, record, branchIssueType))}
          />
        )}
      </ScrollView>

      <ConfirmationModal
        visible={exitConfirmVisible}
        title={t("assistant.exitTitle")}
        description={t("assistant.exitDescription")}
        confirmLabel={t("assistant.exitConfirm")}
        cancelLabel={t("assistant.exitCancel")}
        destructive
        onConfirm={() => {
          setExitConfirmVisible(false);
          logger.info("diagnostic_exited", { serviceId, categoryId, stepIndex: session.currentStepIndex });
          navigation.goBack();
        }}
        onCancel={() => setExitConfirmVisible(false)}
      />
    </SafeAreaView>
  );
}

interface StepQuestionProps {
  stepId: Exclude<StepId, "completion">;
  categoryId: string;
  assistant: ReturnType<typeof useBookingAssistant>;
  onSubmit: (record: AnswerRecord, branchIssueType?: Parameters<typeof submitAnswer>[2]) => void;
}

/** Dispatches to the concrete renderer for the current step's real, fetched data. */
function StepQuestion({ stepId, assistant, onSubmit }: StepQuestionProps) {
  const { t } = useTranslation("discovery");

  switch (stepId) {
    case "issue_type": {
      const options = (assistant.issueTypes.data ?? []).map((it) => ({ id: it.issue_type_id, label: it.name }));
      return (
        <SingleSelectRenderer
          title={t("assistant.issueTypeTitle")}
          options={options}
          selectedId={null}
          onSelect={(option) => {
            const raw = (assistant.issueTypes.data ?? []).find((it) => it.issue_type_id === option.id);
            logger.info("diagnostic_answer_selected", { stepId, optionId: option.id });
            onSubmit(normalizeSingleSelectAnswer("issue_type", option.id, option.label), raw);
          }}
        />
      );
    }
    case "issue_description":
      return (
        <ShortTextRenderer
          title={t("assistant.issueDescriptionTitle")}
          helperText={t("assistant.issueDescriptionHelper")}
          required
          onSubmit={(text) => onSubmit(normalizeShortTextAnswer("issue_description", text))}
        />
      );
    case "photo_boundary":
      return (
        <InformationRenderer
          title={t("assistant.photoBoundaryTitle")}
          body={t("assistant.photoBoundaryBody")}
          required
          onContinue={() => onSubmit(normalizeInformationAcknowledgement("photo_boundary"))}
        />
      );
    case "service_type": {
      const options = (assistant.serviceTypes.data ?? []).map((st) => ({ id: st.type_id, label: st.name, description: st.description }));
      return (
        <SingleSelectRenderer
          title={t("assistant.serviceTypeTitle")}
          options={options}
          selectedId={null}
          onSelect={(option) => onSubmit(normalizeSingleSelectAnswer("service_type", option.id, option.label))}
        />
      );
    }
    case "service_option": {
      const options = (assistant.serviceOptions.data ?? []).map((so) => ({ id: so.service_option_id, label: so.display_name }));
      return <MultiSelectStep stepId="service_option" title={t("assistant.serviceOptionTitle")} options={options} onSubmit={onSubmit} />;
    }
    case "brand": {
      const options = (assistant.brands.data ?? []).map((b) => ({ id: b.brand_id, label: b.name }));
      return (
        <SingleSelectRenderer
          title={t("assistant.brandTitle")}
          options={options}
          selectedId={null}
          onSelect={(option) => onSubmit(normalizeSingleSelectAnswer("brand", option.id, option.label))}
        />
      );
    }
    case "customer_note":
      return (
        <ShortTextRenderer
          title={t("assistant.customerNoteTitle")}
          helperText={t("assistant.customerNoteHelper")}
          onSubmit={(text) => onSubmit(normalizeShortTextAnswer("customer_note", text))}
        />
      );
    default:
      return null;
  }
}

function MultiSelectStep({
  stepId,
  title,
  options,
  onSubmit,
}: {
  stepId: "service_option";
  title: string;
  options: { id: string; label: string }[];
  onSubmit: StepQuestionProps["onSubmit"];
}) {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  return (
    <MultiSelectRenderer
      title={title}
      options={options}
      selectedIds={selectedIds}
      onToggle={(optionId) => setSelectedIds((prev) => (prev.includes(optionId) ? prev.filter((id) => id !== optionId) : [...prev, optionId]))}
      onContinue={() => {
        const labels = options.filter((o) => selectedIds.includes(o.id)).map((o) => o.label);
        onSubmit(normalizeMultiSelectAnswer(stepId, selectedIds, labels));
      }}
    />
  );
}

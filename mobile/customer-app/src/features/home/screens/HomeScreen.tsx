import React, { useEffect } from "react";
import { useNavigation } from "@react-navigation/native";
import { View } from "react-native";
import { ScreenContainer } from "../../../components/layout/ScreenContainer";
import { Stack } from "../../../components/layout/Stack";
import { Section } from "../../../components/layout/Section";
import { AppText } from "../../../components/primitives/AppText";
import { AppAvatar } from "../../../components/primitives/AppAvatar";
import { AppPressable } from "../../../components/primitives/AppPressable";
import { AppIcon } from "../../../components/primitives/AppIcon";
import { Skeleton } from "../../../components/feedback/Skeleton";
import { EmptyState } from "../../../components/feedback/EmptyState";
import { ErrorState } from "../../../components/feedback/ErrorState";
import { OfflineBanner } from "../../../components/feedback/OfflineBanner";
import { useAuthSession } from "../../auth/hooks/use-auth-session";
import { customerInitials } from "../../auth/domain/session";
import { useHomeCategories } from "../queries/home-queries";
import { CategoryGrid } from "../components/CategoryGrid";
import { dayPeriodFromHour, safeFirstName } from "../domain/greeting";
import { evaluateModuleVisibility } from "../domain/module-visibility";
import { resolveModuleRenderer } from "../domain/module-registry";
import type { HomeCategoryItem } from "../domain/discovery-composer";
import { environment } from "../../../config/environment";
import { logger } from "../../../observability/logger";
import type { CategoryId } from "../../../navigation/route-params";

const GREETING_BY_PERIOD = { morning: "Good morning", afternoon: "Good afternoon", evening: "Good evening" } as const;

/** The single real Home module this backend supports today (see CUSTOMER-L5-03-module-registry.md). */
const CATEGORY_GRID_MODULE = { id: "category-grid", type: "category-grid", order: 0, critical: true, requiresAuth: true } as const;

/**
 * The production Home route. Replaces BaselineLandingScreen as the
 * customer's landing screen once authenticated (see startup-route-resolver.ts).
 * Category press now navigates to the real CategoryDetail screen
 * (CUSTOMER-L5-04) instead of the CUSTOMER-L5-03-era toast stub.
 */
export function HomeScreen() {
  const { session, status } = useAuthSession();
  const navigation = useNavigation<any>();
  const categories = useHomeCategories();

  const greeting = GREETING_BY_PERIOD[dayPeriodFromHour(new Date().getHours())];
  const firstName = safeFirstName(session?.fullName);

  function handleCategoryPress(category: HomeCategoryItem) {
    navigation.navigate("CategoryDetail", { categoryId: category.id as CategoryId });
  }

  // Routed through the same centralized registry/visibility layer every
  // module (real or future) must go through — CUSTOMER-L5-03 §7/§9. Today
  // there is exactly one recognized, critical module; a critical module
  // resolving to anything other than VISIBLE for an authenticated customer
  // means something is actually wrong (not a normal empty state), so it's
  // surfaced as the page-level error rather than silently rendering nothing.
  const resolvedRenderer = resolveModuleRenderer(CATEGORY_GRID_MODULE.type);
  const visibility = resolvedRenderer.recognized
    ? evaluateModuleVisibility(CATEGORY_GRID_MODULE, { authenticated: status === "authenticated", appVersion: environment.buildVersion })
    : "CONFIGURATION_INVALID";
  const criticalModuleUnavailable = CATEGORY_GRID_MODULE.critical && visibility !== "VISIBLE";

  useEffect(() => {
    if (criticalModuleUnavailable) {
      logger.warn("home_module_render_failed", { moduleType: CATEGORY_GRID_MODULE.type, visibility });
    }
  }, [criticalModuleUnavailable, visibility]);

  return (
    <ScreenContainer onRefresh={() => void categories.refetch()} refreshing={categories.isRefetching}>
      <Stack gap={7}>
        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
          <View>
            <AppText variant="headingLarge" accessibilityRole="header">
              {firstName ? `${greeting}, ${firstName}` : greeting}
            </AppText>
          </View>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
            <AppPressable accessibilityLabel="Search services and categories" onPress={() => navigation.navigate("Search")}>
              <AppIcon name="search" size="md" color="iconPrimary" />
            </AppPressable>
            <AppPressable accessibilityLabel="View my bookings" onPress={() => navigation.navigate("BookingsList")}>
              <AppIcon name="list" size="md" color="iconPrimary" />
            </AppPressable>
            <AppPressable
              accessibilityLabel="Open your profile"
              accessibilityHint="Opens your account profile"
              onPress={() => navigation.navigate("Profile")}
              enforceMinTouchTarget={false}
            >
              <AppAvatar accessibilityLabel="Your profile" imageUrl={session?.avatarUrl} initials={session ? customerInitials(session) : undefined} size="md" />
            </AppPressable>
          </View>
        </View>

        <OfflineBanner />

        {criticalModuleUnavailable ? (
          <ErrorState title="Home is temporarily unavailable" description="Please sign in again or try later." />
        ) : (
          <Section title="Services">
            {categories.isLoading ? (
              <Stack gap={4}>
                <Skeleton height={96} />
                <Skeleton height={96} width="80%" />
              </Stack>
            ) : categories.isError ? (
              <ErrorState title="Couldn't load services" description="Something went wrong on our end." onRetry={() => void categories.refetch()} />
            ) : categories.data && categories.data.items.length > 0 ? (
              <CategoryGrid categories={categories.data.items} onSelect={handleCategoryPress} />
            ) : (
              <EmptyState title="No services available" description="Please check back later." icon="search" />
            )}
          </Section>
        )}
      </Stack>
    </ScreenContainer>
  );
}

import React from "react";
import { Image, Platform, Pressable, View } from "react-native";
import { createBottomTabNavigator, type BottomTabBarProps } from "@react-navigation/bottom-tabs";
import { CommonActions } from "@react-navigation/native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { LinearGradient } from "expo-linear-gradient";
import { CustomerTabsParamList, CustomerTabName } from "./routeTypes";
import { AppLucideIcon, AppText, type AppLucideName } from "../components";
import { useTheme } from "../design-system/theme";
import { HomeScreen } from "../screens/home/HomeScreen";
import { MyBookingsScreen } from "../screens/bookings/MyBookingsScreen";
import { BookingChatScreen } from "../screens/bookingChat/BookingChatScreen";
import { HelpSupportScreen } from "../screens/support/HelpSupportScreen";
import { ProfileScreen } from "../screens/profile/ProfileScreen";
import { saveLastSelectedTab } from "./navigationPersistence";
import { FuvayTile } from "../components/fuvay/FuvayTile";

const Tab = createBottomTabNavigator<CustomerTabsParamList>();

const TAB_ICON: Record<Exclude<CustomerTabName, "Assistant">, AppLucideName> = {
  Home: "home-outline",
  Bookings: "calendar-outline",
  Support: "lifebuoy-outline",
  Profile: "person-outline",
};

function FuvayTabBar({ state, navigation }: BottomTabBarProps) {
  const { theme } = useTheme();
  const insets = useSafeAreaInsets();
  const bottomInset = Math.max(insets.bottom, Platform.OS === "android" ? 16 : 8);
  const t = theme.fuvay;
  const assistantIndex = state.routes.findIndex(route => route.name === "Assistant");
  const assistantRoute = state.routes[assistantIndex];
  const assistantActive = state.index === assistantIndex;
  const onAssistantPress = () => {
    if (!assistantRoute) return;
    const event = navigation.emit({ type: "tabPress", target: assistantRoute.key, canPreventDefault: true });
    if (!assistantActive && !event.defaultPrevented) navigation.navigate(assistantRoute.name, assistantRoute.params);
  };

  return (
    <LinearGradient colors={t.surfaces.navBg as [string, string]} style={{ paddingHorizontal: 16, paddingTop: 28, paddingBottom: 12 + bottomInset, borderTopWidth: 1, borderTopColor: t.surfaces.edge, overflow: "visible" }}>
      <View style={{ position: "relative", overflow: "visible", zIndex: 100 }}>
        <LinearGradient colors={t.surfaces.navBg as [string, string]} style={{ minHeight: 60, borderRadius: 999, padding: 7, flexDirection: "row", alignItems: "center", gap: 4, borderWidth: 1, borderColor: t.surfaces.edge, shadowColor: t.softShadow.color, shadowOffset: { width: 0, height: t.softShadow.offsetY }, shadowRadius: t.softShadow.radius, shadowOpacity: t.softShadow.opacity }}>
          {state.routes.map((route, index) => {
          const active = state.index === index;
          const isAssistant = route.name === "Assistant";
          // The reference navigation only expands Home into a labelled pill.
          // Other destinations stay icon-only when selected so the bar never
          // reflows or exposes Bookings/Support/Account text after a tap.
          const showLabel = active && route.name === "Home";
          const icon = route.name === "Assistant" ? null : TAB_ICON[route.name as Exclude<CustomerTabName, "Assistant">];
          const onPress = () => {
            const event = navigation.emit({ type: "tabPress", target: route.key, canPreventDefault: true });
            if (!active && !event.defaultPrevented) navigation.navigate(route.name, route.params);
          };
          if (isAssistant) {
            return <View key={route.key} style={{ width: 66, height: 46 }} />;
          }
          // Only the labelled Home pill needs contrast text. Icon-only active
          // destinations use the brand blue directly so their glyph remains
          // visible against the navigation surface in both themes.
          const foreground = showLabel
            ? t.ink(t.accents.a2)
            : active
              ? t.accents.a2
              : t.surfaces.sub;
          return (
            <Pressable key={route.key} accessibilityRole="button" accessibilityState={{ selected: active }} accessibilityLabel={route.name} onPress={onPress} style={({ pressed }) => ({ flex: showLabel ? 1.5 : 1, minHeight: 46, paddingHorizontal: showLabel ? 12 : 8, borderRadius: 999, backgroundColor: showLabel ? t.accents.a2 : "transparent", flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, opacity: pressed ? 0.76 : 1 })}>
              <AppLucideIcon name={icon!} size={19} color={foreground} strokeWidth={2} />
              {showLabel ? <AppText variant="button" numberOfLines={1} style={{ color: foreground }}>Home</AppText> : null}
            </Pressable>
          );
          })}
        </LinearGradient>
        {assistantRoute ? (
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ selected: assistantActive }}
            accessibilityLabel="Assistant"
            onPress={onAssistantPress}
            style={({ pressed }) => ({
              position: "absolute",
              left: "50%",
              top: -22,
              marginLeft: -31,
              width: 62,
              height: 62,
              borderRadius: 31,
              opacity: pressed ? 0.76 : 1,
              zIndex: 100,
              elevation: 24,
            })}
          >
            <FuvayTile style={{ width: 62, height: 62 }} borderRadius={31} inset={9}>
              <Image
                source={t.isDark ? require("../../assets/fuvay-mark-dark.png") : require("../../assets/fuvay-mark-light.png")}
                resizeMode="contain"
                style={{ width: 27, height: 27 }}
                accessibilityLabel="Fuvay AI"
                accessibilityIgnoresInvertColors
              />
            </FuvayTile>
          </Pressable>
        ) : null}
      </View>
    </LinearGradient>
  );
}

/** Five customer tabs, exact required order: Home, Bookings, Assistant,
 * Support, Profile. No Chat/Offers/Wallet/Payments/Providers tabs. */
export function CustomerTabs() {
  return (
    <Tab.Navigator
      tabBar={props => <FuvayTabBar {...props} />}
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarAccessibilityLabel: route.name,
        tabBarHideOnKeyboard: true,
      })}
      screenListeners={{
        state: e => {
          const state = e.data.state;
          const activeRoute = state?.routes[state.index]?.name as CustomerTabName | undefined;
          if (activeRoute) saveLastSelectedTab(activeRoute);
        },
      }}
    >
      <Tab.Screen
        name="Home"
        component={HomeScreen}
      />
      <Tab.Screen
        name="Bookings"
        component={MyBookingsScreen}
      />
      {/* A tab keeps the params it was last navigated with. So once a customer
          had entered the Assistant from a service card on Home, every later tap
          on the tab itself re-entered with that category still attached -- the
          assistant opened straight into AC questions for someone who had asked
          for nothing. Entering from the tab is a category-less start, so the
          stale params are cleared (merge: false replaces them outright).

          Only when the tab is NOT already focused: tapping the tab you are
          standing on must not discard a conversation in progress. */}
      <Tab.Screen
        name="Assistant"
        component={BookingChatScreen}
        listeners={({ navigation }) => ({
          tabPress: () => {
            if (navigation.isFocused()) return;
            navigation.dispatch(
              CommonActions.navigate("Assistant", undefined, { merge: false }),
            );
          },
        })}
      />
      <Tab.Screen
        name="Support"
        component={HelpSupportScreen}
      />
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
      />
    </Tab.Navigator>
  );
}

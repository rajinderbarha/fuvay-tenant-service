import { createNavigationContainerRef } from "@react-navigation/native";
import { RootStackParamList } from "./routeTypes";

export const navigationRef = createNavigationContainerRef<RootStackParamList>();

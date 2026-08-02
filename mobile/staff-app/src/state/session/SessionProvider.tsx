/**
 * The live session provider is mounted at src/navigation/session/SessionProvider.tsx
 * (Phase E's file, extended in Phase F to run the real bootstrap/refresh/
 * event/network/lifecycle engine from services/auth + services/api -- see
 * that file's comments). This file re-exports it under the module path the
 * Phase F spec's required structure calls for, so there is exactly ONE
 * mounted provider (no redundant second bootstrap sequence / duplicate
 * NetInfo or AppState subscriptions) while both required file locations
 * resolve to the same, single implementation.
 */
export { SessionProvider, useSession, useRootDestination } from "../../navigation/session/SessionProvider";

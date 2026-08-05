import { registerRootComponent } from "expo";
// TEMPORARY diagnostic -- forwards uncaught JS errors to the backend capture
// log so a post-response crash can be seen. Delete with
// src/root/debugClientErrorReporter.ts.
import { installDebugClientErrorReporter } from "./src/root/debugClientErrorReporter";
import App from "./src/root/App";

installDebugClientErrorReporter();
registerRootComponent(App);

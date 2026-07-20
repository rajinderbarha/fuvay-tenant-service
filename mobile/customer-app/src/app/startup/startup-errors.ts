import type { StartupErrorCategory } from "./startup-types";

export class StartupError extends Error {
  readonly category: StartupErrorCategory;
  readonly errorReferenceId: string;

  constructor(category: StartupErrorCategory, message: string) {
    super(message);
    this.name = "StartupError";
    this.category = category;
    this.errorReferenceId = newStartupErrorReferenceId();
  }
}

export function newStartupErrorReferenceId(): string {
  return `startup_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

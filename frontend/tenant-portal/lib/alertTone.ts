/**
 * The sound an alert makes.
 *
 * Two notes, synthesised — no audio file to ship, cache, or 404. What matters is that a
 * provider can tell WHICH kind of alert arrived without looking at the screen:
 *
 *   success  — rising pair (C5 -> E5). Something good happened.
 *   warning  — falling pair, lower and slower. Something needs attention.
 *
 * Rising for good and falling for bad is not decoration; it is the one convention people
 * already read without being taught, and it means the sound carries the same meaning as
 * the popup's colour rather than just announcing that a popup exists.
 *
 * Three things this deliberately does:
 *
 *  - Fails silently. Browsers refuse to start audio before the user has interacted with
 *    the page, and some block it entirely. A dashboard must never break, or log noise,
 *    because a chime could not play.
 *  - Respects a stored preference, so a provider working in a quiet office can turn it
 *    off and stay off (see `setAlertSoundEnabled`).
 *  - Keeps the volume low and the tone short. This fires while somebody is working; it
 *    is a notification, not an alarm.
 */

const PREF_KEY = "fuvay.dashboard.alertSound";

/** Quiet by design: audible in a room, not startling in a headset. */
const GAIN = 0.06;
const NOTE_MS = 110;

type Tone = "success" | "warning" | "critical" | "info";

/** Frequencies in Hz. The pair is the message: up is good, down needs attention. */
const NOTES: Record<Tone, [number, number]> = {
  success: [523.25, 659.25],   // C5 -> E5, rising
  warning: [440.0, 349.23],    // A4 -> F4, falling
  critical: [440.0, 293.66],   // A4 -> D4, falling further
  info: [523.25, 523.25],      // single repeated note: present, not directional
};

export function isAlertSoundEnabled(): boolean {
  if (typeof window === "undefined") return false;
  try {
    // Default ON: an alert nobody hears is the problem being solved. Opting out is one
    // click, and the choice sticks.
    return window.localStorage.getItem(PREF_KEY) !== "off";
  } catch {
    return true;
  }
}

export function setAlertSoundEnabled(enabled: boolean): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(PREF_KEY, enabled ? "on" : "off");
  } catch {
    /* A blocked storage must not stop the sound working for this session. */
  }
}

/**
 * Plays the tone for a severity. Returns whether a sound was actually started, so a
 * caller can tell "played" from "silently skipped" instead of assuming.
 */
export function playAlertTone(tone: Tone): boolean {
  if (typeof window === "undefined") return false;
  if (!isAlertSoundEnabled()) return false;

  // Honour the OS "reduce motion" hint as a proxy for "fewer interruptions". Someone who
  // has asked their machine to calm down has already answered this question.
  try {
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return false;
  } catch {
    /* matchMedia missing is not a reason to refuse. */
  }

  const AudioCtx = window.AudioContext
    ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!AudioCtx) return false;

  try {
    const ctx = new AudioCtx();
    // Before any user gesture the context starts suspended and nothing will be heard.
    // Reported honestly rather than pretending it played.
    if (ctx.state === "suspended") {
      void ctx.resume().catch(() => {});
    }

    const [first, second] = NOTES[tone] ?? NOTES.info;
    const start = ctx.currentTime;

    [first, second].forEach((frequency, index) => {
      const at = start + (index * NOTE_MS) / 1000;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      // A sine is the least piercing shape at this volume; a square wave at the same
      // gain reads as an error beep from a much older piece of software.
      osc.type = "sine";
      osc.frequency.value = frequency;
      // Ramped in and out: an abrupt start and stop produces an audible click.
      gain.gain.setValueAtTime(0, at);
      gain.gain.linearRampToValueAtTime(GAIN, at + 0.01);
      gain.gain.linearRampToValueAtTime(0, at + NOTE_MS / 1000);
      osc.connect(gain).connect(ctx.destination);
      osc.start(at);
      osc.stop(at + NOTE_MS / 1000 + 0.02);
    });

    // Released once the pair has finished, so a long session does not accumulate
    // audio contexts (browsers cap how many a page may hold).
    window.setTimeout(() => { void ctx.close().catch(() => {}); }, NOTE_MS * 2 + 250);
    return ctx.state !== "suspended";
  } catch {
    // Blocked, unsupported, or out of contexts. Silence is an acceptable outcome; a
    // thrown error on a dashboard is not.
    return false;
  }
}

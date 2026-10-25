// Outcome sounds (v1's sound.js, ADR-0020): a short tone when a notice
// reports what just happened, so someone on the floor hears that a save
// went through without looking. Synthesised with Web Audio: no audio
// files, no library.
//
// The tone rides on the notice the server sends (data-sound-tag), never
// on a button: a sound at tap time would say "done" before the server had
// done anything. Browsers block sound on a fresh page until it is tapped,
// except in an installed app, so the first sound in a plain browser tab
// may not play. That is a missing nicety, never a missing fact: the notice
// is on the screen either way.

export const STORAGE_KEY = "soundEnabled";

// Each note: [frequency in Hz, start in seconds, length in seconds, peak].
export const TONES = {
  // Two notes rising: the shape everyone reads as "went through".
  success: [
    [660, 0, 0.09, 0.05],
    [880, 0.075, 0.11, 0.05],
  ],
  // Two notes falling, lower and blunter: told apart from success
  // without looking.
  error: [
    [320, 0, 0.11, 0.06],
    [240, 0.09, 0.15, 0.06],
  ],
  // One flat note: something happened, it was not a failure, look up.
  warning: [[500, 0, 0.16, 0.05]],
  // One short, quieter high note: a question is on the screen. The card
  // already asks for attention, so the sound only marks the moment.
  prompt: [[950, 0, 0.07, 0.03]],
};

// Every tone is made louder from this one place, so the tones stay in
// proportion. The limit stops a note before the speaker distorts.
const VOLUME_SCALE = 14;
export const PEAK_LIMIT = 0.98;

// The server's message tags that make a sound. Info and debug stay silent:
// a sound for every notice would teach everyone to stop hearing the ones
// that matter.
const TAG_TONES = { success: "success", error: "error", warning: "warning" };

// One sound per page, whatever the number of notices: three errors are one
// failed action reported three ways. An error wins over everything else,
// because what went wrong is what is worth hearing.
export function chooseTone(tags) {
  let chosen = null;
  for (const tag of tags) {
    const tone = TAG_TONES[tag];
    if (tone === "error") {
      return "error";
    }
    chosen = chosen || tone || null;
  }
  return chosen;
}

// On unless this device turned it off.
export function isEnabled(stored) {
  return stored !== "off";
}

export function loudness(peak) {
  return Math.min(peak * VOLUME_SCALE, PEAK_LIMIT);
}

// Everything below needs a browser.

let context = null;

function audio() {
  if (!context) {
    const Context = window.AudioContext || window.webkitAudioContext;
    context = Context ? new Context() : null;
  }
  return context;
}

// The volume rises and falls on every note: a note started or stopped at
// full volume clicks, and on a phone speaker the click is louder than the
// note.
function note(ctx, [frequency, when, length, peak]) {
  const oscillator = ctx.createOscillator();
  const gain = ctx.createGain();
  const start = ctx.currentTime + when;
  oscillator.frequency.setValueAtTime(frequency, start);
  gain.gain.setValueAtTime(0.0001, start);
  gain.gain.exponentialRampToValueAtTime(
    loudness(peak),
    start + Math.min(0.008, length * 0.4),
  );
  gain.gain.exponentialRampToValueAtTime(0.0001, start + length);
  oscillator.connect(gain).connect(ctx.destination);
  oscillator.start(start);
  oscillator.stop(start + length + 0.02);
}

function readEnabled() {
  try {
    return isEnabled(localStorage.getItem(STORAGE_KEY));
  } catch {
    return true;
  }
}

export function setEnabled(on) {
  try {
    localStorage.setItem(STORAGE_KEY, on ? "on" : "off");
  } catch {
    // Private browsing keeps no setting; the sound stays on.
  }
}

// A sound never breaks a page: every failure here is silent.
export function play(kind) {
  const notes = TONES[kind];
  if (!notes || !readEnabled()) {
    return;
  }
  try {
    const ctx = audio();
    if (!ctx) {
      return;
    }
    const sound = () => notes.forEach((n) => note(ctx, n));
    if (ctx.state === "suspended") {
      ctx.resume().then(sound, () => {});
    } else {
      sound();
    }
  } catch {
    // No sound; the notice still says it.
  }
}

// Plays the one tone for the notices inside root.
export function announce(root = document) {
  const notices = root.querySelectorAll("[data-sound-tag]");
  const tone = chooseTone([...notices].map((n) => n.dataset.soundTag));
  if (tone) {
    play(tone);
  }
}

if (typeof document !== "undefined") {
  announce();
}

// Browser speech narrator (Web Speech API, uses the OS voices — works offline on macOS).
// Speaks one sentence at a time so pause/resume is reliable across browsers.

const PREFERRED = [
  'Ava (Premium)', 'Evan (Premium)', 'Zoe (Premium)', 'Allison (Premium)', 'Samantha (Enhanced)', 'Ava (Enhanced)',
  'Google US English', 'Microsoft Aria Online (Natural) - English (United States)', 'Samantha', 'Daniel', 'Karen', 'Moira', 'Alex',
];

// macOS ships novelty voices; never offer them in a client presentation.
const NOVELTY = /^(Albert|Bad News|Bahh|Bells|Boing|Bubbles|Cellos|Fred|Good News|Grandma|Grandpa|Jester|Junior|Kathy|Organ|Ralph|Rocko|Superstar|Trinoids|Whisper|Wobble|Zarvox)\b/;

export function listVoices(): SpeechSynthesisVoice[] {
  if (typeof window === 'undefined' || !window.speechSynthesis) return [];
  const vs = window.speechSynthesis.getVoices().filter((v) => v.lang.startsWith('en') && !NOVELTY.test(v.name));
  const rank = (v: SpeechSynthesisVoice) => { const i = PREFERRED.indexOf(v.name); return i === -1 ? 99 : i; };
  return vs.sort((a, b) => rank(a) - rank(b) || a.name.localeCompare(b.name));
}

export function defaultVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | undefined {
  for (const n of PREFERRED) { const v = voices.find((x) => x.name === n); if (v) return v; }
  return voices.find((v) => v.lang === 'en-US') ?? voices[0];
}

export function onVoicesChanged(cb: () => void) {
  if (!window.speechSynthesis) return () => {};
  window.speechSynthesis.addEventListener('voiceschanged', cb);
  return () => window.speechSynthesis.removeEventListener('voiceschanged', cb);
}

export function sentences(text: string): string[] {
  return (text.match(/[^.!?]+[.!?]+(\s|$)|[^.!?]+$/g) ?? [text]).map((s) => s.trim()).filter(Boolean);
}

/** Speak one sentence. Resolves true when finished, false when cancelled. */
export function speakOne(text: string, opts: { voice?: SpeechSynthesisVoice; rate: number }): Promise<boolean> {
  return new Promise((resolve) => {
    const ss = window.speechSynthesis;
    if (!ss) { resolve(true); return; }
    const u = new SpeechSynthesisUtterance(text);
    if (opts.voice) u.voice = opts.voice;
    u.rate = opts.rate;
    u.pitch = 1;
    let done = false;
    const finish = (ok: boolean) => { if (!done) { done = true; clearInterval(keep); resolve(ok); } };
    u.onend = () => finish(true);
    u.onerror = (e) => finish(e.error !== 'interrupted' && e.error !== 'canceled');
    // Chrome stops long utterances after ~15 s unless nudged
    const keep = setInterval(() => { if (ss.speaking && !ss.paused) { ss.pause(); ss.resume(); } }, 10000);
    ss.speak(u);
  });
}

export function cancelSpeech() { try { window.speechSynthesis?.cancel(); } catch { /* ignore */ } }

/** Reading-time estimate when the voice is muted (ms). */
export function readMs(text: string, pace: number) { return Math.max(1400, (text.split(/\s+/).length / 2.6) * 1000) / pace; }

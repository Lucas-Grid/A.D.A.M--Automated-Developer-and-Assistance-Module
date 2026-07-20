"""Voice INPUT for Jarvis (STT / speech-to-command).

Gives Jarvis ears so it can be "controlled by the user's voice commands":

- A background listener that waits for the wake word "Jarvis", then transcribes
  the following phrase and hands it to a callback (which routes it to the
  orchestrator / desktop tools).
- Continuous "hands-free" mode (no wake word) is also supported.

Backends (tried in order, all optional -- never crash the app):
  1. Vosk  (offline, tiny model, no API key)  -- preferred for privacy/local.
  2. SpeechRecognition + PyAudio (online via Google/Whisper, or offline if a
     local recognizer is configured).

If no backend is installed, ``VoiceInput.available`` is False and the GUI/CLI
shows a clear "voice input not installed" notice instead of failing. Install
with ``pip install vosk`` (plus a model) or ``pip install SpeechRecognition
pyaudio``.

The class is backend-agnostic: it just yields strings via the callback.
"""
from __future__ import annotations

import os
import threading
from typing import Callable, Optional

WakeWord = "jarvis"


class VoiceInput:
    """Speech-to-text listener with wake-word + hands-free modes.

    Usage::

        vi = VoiceInput(on_command=handle_text)
        vi.start()                 # blocks in a daemon thread
        vi.set_mode("wake")        # or "continuous"
        vi.stop()
    """

    def __init__(
        self,
        on_command: Callable[[str], None],
        wake_word: str = WakeWord,
        sample_rate: int = 16000,
        barge_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        self.on_command = on_command
        self.wake_word = wake_word.lower()
        self.sample_rate = sample_rate
        self.mode: str = "wake"  # "wake" | "continuous"
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._engine = None
        self._engine_kind: Optional[str] = None
        # Buffer of recent partial+fuzz text so a wake word spoken in one
        # utterance and the command in the next (or mid-sentence) are both seen.
        self._recent: list[str] = []
        # Called when the user starts speaking (energy/voice detected) so the
        # assistant can interrupt any in-progress reply (barge-in).
        self.barge_callback = barge_callback
        self._init_engine()

    # ---- capability -------------------------------------------------------
    @property
    def available(self) -> bool:
        return self._engine is not None

    def _init_engine(self) -> None:
        # 1) Vosk (offline, no key)
        try:
            import vosk  # noqa: F401
            import sounddevice  # noqa: F401

            self._engine = ("vosk", None)
            self._engine_kind = "vosk"
            return
        except Exception:
            pass
        # 2) SpeechRecognition + PyAudio (online by default)
        try:
            import speech_recognition as sr  # noqa: F401

            self._engine = ("sr", sr.Recognizer())
            self._engine_kind = "sr"
            return
        except Exception:
            pass
        self._engine = None
        self._engine_kind = None

    # ---- control ----------------------------------------------------------
    def set_mode(self, mode: str) -> None:
        self.mode = "continuous" if mode == "continuous" else "wake"

    def start(self) -> bool:
        """Start the listener thread. Returns False if no backend is available."""
        if not self.available:
            return False
        if self._running:
            return True
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    # ---- engine loops -----------------------------------------------------
    def _loop(self) -> None:
        if self._engine_kind == "vosk":
            self._loop_vosk()
        elif self._engine_kind == "sr":
            self._loop_sr()

    def _loop_vosk(self) -> None:
        import queue
        import sounddevice as sd
        import vosk

        model_path = _vosk_model_path()
        if model_path is None:
            print("[voice-input] vosk installed but no model found; "
                  "download e.g. vosk-model-small-en-us to enable offline STT.")
            return
        model = vosk.Model(model_path)
        rec = vosk.KaldiRecognizer(model, self.sample_rate)
        q: "queue.Queue" = queue.Queue()

        import struct

        def _rms(indata: bytes) -> float:
            try:
                nums = struct.unpack(f"<{len(indata) // 2}h", indata)
                return (sum(x * x for x in nums) / max(1, len(nums))) ** 0.5
            except Exception:
                return 0.0

        def _cb(indata, frames, t, status):
            q.put(bytes(indata))

        # Barge-in via SPEECH ONSET detection (not raw loudness): Jarvis's own
        # speaker output is steady-loud, so a simple threshold would cut him
        # off mid-sentence (or never fire). We fire only on a rising edge from
        # quiet -> loud (a real voice starting after silence), plus a short
        # refractory window so one utterance triggers at most one interrupt.
        SPEECH_ONSET = 350.0   # RMS that counts as "someone is talking"
        QUIET = 120.0          # below this = silence
        REFRACTORY_S = 1.2     # min seconds between barge triggers
        import time as _t
        was_quiet = True
        last_barge = 0.0

        # Crash-safe: if the mic stream dies, restart it instead of ending the
        # listener (the assistant must keep listening at all times).
        while self._running:
            try:
                with sd.RawInputStream(samplerate=self.sample_rate, blocksize=8000,
                                       dtype="int16", channels=1, callback=_cb):
                    while self._running:
                        data = q.get()
                        energy = _rms(data)
                        # Detect a fresh utterance: silence -> speech onset.
                        if was_quiet and energy > SPEECH_ONSET:
                            now = _t.time()
                            if now - last_barge > REFRACTORY_S and self.barge_callback is not None:
                                last_barge = now
                                try:
                                    self.barge_callback()
                                except Exception:
                                    pass
                        was_quiet = energy < QUIET
                        if rec.AcceptWaveform(data):
                            text = _vosk_text(rec.Result())
                            self._handle(text)
                        else:
                            partial = _vosk_text(rec.PartialResult())
                            if partial:
                                self._recent.append(partial)
                                if len(self._recent) > 6:
                                    self._recent.pop(0)
                                self._handle(partial)
            except Exception as e:
                print(f"[voice-input] mic stream error, restarting: {e}")
                import time as _t2
                _t2.sleep(1)

    def _loop_sr(self) -> None:
        import speech_recognition as sr

        rec = self._engine[1]
        with sr.Microphone(sample_rate=self.sample_rate) as src:
            rec.adjust_for_ambient_noise(src, duration=0.5)
            while self._running:
                try:
                    audio = rec.listen(src, phrase_time_limit=6, timeout=8)
                    text = rec.recognize_google(audio)
                    self._handle(text)
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    continue
                except Exception as e:  # mic dropped, net blip, etc.
                    print(f"[voice-input] transient STT error: {e}")
                    continue

    # ---- offline / testable transcription ---------------------------------
    def transcribe_wav(self, path: str) -> str:
        """Transcribe a WAV file to text using the active engine.

        Used by the live Vosk loop conceptually and exposed for tests / batch
        transcription. Returns '' if no STT engine is available.
        """
        if self._engine_kind != "vosk":
            return ""
        import json
        import soundfile as sf
        import vosk

        model_path = _vosk_model_path()
        if model_path is None:
            return ""
        if not os.path.isfile(path):
            return ""
        try:
            model = vosk.Model(model_path)
            data, sr = sf.read(path, dtype="int16")
        except Exception:
            return ""
        if sr != self.sample_rate:
            data = _resample(data, sr, self.sample_rate)
            sr = self.sample_rate
        rec = vosk.KaldiRecognizer(model, self.sample_rate)
        rec.AcceptWaveform(data.tobytes())
        return _vosk_text(rec.Result())

    # ---- wake-word routing ------------------------------------------------
    def _handle(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        low = text.lower()
        if self.mode == "continuous":
            self.on_command(text)
            self._recent.clear()
            return
        # wake mode: the wake word may appear in this utterance OR in a recent
        # buffered partial. If the wake word is present, emit everything after
        # it (this utterance's command); if not but a recent buffer already
        # contained it, treat THIS as the command. Debounced via _recent clear.
        if self.wake_word in low:
            rest = low.split(self.wake_word, 1)[1]
            rest = rest.lstrip(" ,:.-\n")
            self._recent.clear()
            if rest:
                self.on_command(rest)
            return
        # No wake word in this utterance: if a recent partial already said the
        # wake word, this is the command. Otherwise ignore.
        if any(self.wake_word in b for b in self._recent):
            combined = " ".join(self._recent[-3:] + [low])
            self._recent.clear()
            cmd = combined.replace(self.wake_word, "", 1).strip(" ,:.-\n")
            if cmd:
                self.on_command(cmd)


def _vosk_text(result_json: str) -> str:
    import json

    try:
        return json.loads(result_json).get("text", "")
    except Exception:
        return ""


def _resample(data, src_sr: int, dst_sr: int):
    """Resample int16 PCM to dst_sr. Uses resampy if present, else scipy."""
    import numpy as np

    if src_sr == dst_sr:
        return data
    try:
        import resampy

        return resampy.resample(data.astype("float64"), src_sr, dst_sr).astype("int16")
    except Exception:
        from scipy.signal import resample as _scipy_resample

        n = int(round(len(data) * dst_sr / src_sr))
        return _scipy_resample(data, n).astype("int16")


def _vosk_model_path() -> Optional[str]:
    """Best-effort search for a Vosk model directory."""
    import os
    import glob

    env = os.environ.get("VOSK_MODEL_PATH")
    if env and os.path.isdir(env):
        return env
    # Common local spots.
    for base in (
        os.path.expanduser("~/vosk-models"),
        os.path.join(os.getcwd(), "vosk-model"),
        r"C:\vosk-models",
    ):
        if os.path.isdir(base):
            hits = glob.glob(os.path.join(base, "vosk-model-*"))
            if hits:
                return sorted(hits)[-1]
    return None

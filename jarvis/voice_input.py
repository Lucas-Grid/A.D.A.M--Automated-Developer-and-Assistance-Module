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
    ) -> None:
        self.on_command = on_command
        self.wake_word = wake_word.lower()
        self.sample_rate = sample_rate
        self.mode: str = "wake"  # "wake" | "continuous"
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._engine = None
        self._engine_kind: Optional[str] = None
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
            # No model downloaded; emit a one-time notice and idle.
            self.on_command("")  # no-op; GUI notices availability separately
            print("[voice-input] vosk installed but no model found; "
                  "download e.g. vosk-model-small-en-us to enable offline STT.")
            return
        model = vosk.Model(model_path)
        rec = vosk.KaldiRecognizer(model, self.sample_rate)
        q: "queue.Queue" = queue.Queue()

        def _cb(indata, frames, t, status):
            q.put(bytes(indata))

        with sd.RawInputStream(samplerate=self.sample_rate, blocksize=8000,
                               dtype="int16", channels=1, callback=_cb):
            while self._running:
                data = q.get()
                if rec.AcceptWaveform(data):
                    text = _vosk_text(rec.Result())
                    self._handle(text)

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
            return
        # wake mode: require the wake word, then pass the remainder.
        if self.wake_word in low:
            # strip the wake word (and a following comma/colon) and emit rest.
            rest = low.split(self.wake_word, 1)[1]
            rest = rest.lstrip(" ,:.-")
            if rest:
                self.on_command(rest)
        # else: ignore (not addressed to Jarvis)


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

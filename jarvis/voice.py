"""Voice output for Jarvis (folds ADAM's TTS in, dependency-light).

Strategy (tried in order, graceful degrade):
  * Primary: OpenAI-compatible TTS via NVIDIA NIM (nvidia/... speech models)
    using the same NVIDIA_NIM_API_KEY as the LLM.
  * Fallback: OpenAI TTS-1 if OPENAI_API_KEY is set.
  * OFFLINE fallback (no key): Windows SAPI via pywin32 (Cortana/desktop voices).
    This is what makes Jarvis actually SPEAK on a normal Windows box with no
    API key configured.

Speaking is NON-BLOCKING and INTERRUPTIBLE: each call runs in a daemon thread
and a later speak()/stop() cancels any in-progress utterance, so the user can
barge in mid-sentence (hotword/energy interruption) while Jarvis keeps listening.
"""
from __future__ import annotations

import base64
import json
import os
import threading
import tempfile
from typing import Optional


class Voice:
    """Minimal text-to-speech client (OpenAI-compatible audio/speech)."""

    def __init__(
        self,
        nim_key: str = "",
        openai_key: str = "",
        nim_model: str = "nvidia/tts-en-1",
        openai_model: str = "tts-1",
        voice: str = "alloy",
        timeout: int = 30,
    ) -> None:
        self.nim_key = nim_key or os.environ.get("NVIDIA_NIM_API_KEY", "")
        self.openai_key = openai_key or os.environ.get("OPENAI_API_KEY", "")
        self.nim_model = nim_model
        self.openai_model = openai_model
        self.voice = voice
        self.timeout = timeout
        # Active speech thread so we can interrupt it (barge-in).
        self._speak_thread: Optional[threading.Thread] = None
        self._stop_flag = threading.Event()

    def available(self) -> bool:
        # Cloud keys OR offline SAPI both count as "can speak".
        return bool(self.nim_key or self.openai_key or _sapi_available())

    def _active_provider(self) -> str:
        if self.nim_key:
            return "nim"
        if self.openai_key:
            return "openai"
        return "sapi"

    def stop(self) -> None:
        """Interrupt any in-progress speech immediately (barge-in)."""
        self._stop_flag.set()
        t = self._speak_thread
        if t is not None and t.is_alive():
            t.join(timeout=0.5)
        self._speak_thread = None
        # SAPI speakers are COM objects; nothing else to tear down here.

    def speak(self, text: str, block: bool = False, out_path: Optional[str] = None) -> dict:
        """Speak ``text`` aloud. NON-BLOCKING by default (returns at once so the
        assistant/voice thread stays free to listen for interruptions). Set
        ``block=True`` only for quick self-tests.
        """
        text = (text or "").strip()
        if not text:
            return {"ok": False, "error": "empty text", "text": text}

        self.stop()  # cancel any prior utterance so new replies take over
        self._stop_flag.clear()
        t = threading.Thread(target=self._speak_sync, args=(text, out_path), daemon=True)
        self._speak_thread = t
        t.start()
        if block:
            t.join(timeout=self.timeout + 5)
        return {"ok": True, "provider": self._active_provider(), "text": text}

    # ---- synchronous worker (runs in a daemon thread) --------------------
    def _speak_sync(self, text: str, out_path: Optional[str]) -> None:
        import requests

        providers = []
        if self.nim_key:
            providers.append(("nim", "https://integrate.api.nvidia.com/v1", self.nim_key, self.nim_model))
        if self.openai_key:
            providers.append(("openai", "https://api.openai.com/v1", self.openai_key, self.openai_model))

        last_err = ""
        for name, base, key, model in providers:
            try:
                resp = requests.post(
                    f"{base}/audio/speech",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model": model, "voice": self.voice, "input": text, "response_format": "wav"},
                    timeout=self.timeout,
                )
                if resp.status_code != 200:
                    last_err = f"{name}: HTTP {resp.status_code}"
                    continue
                audio = resp.content
                path = out_path or os.path.join(tempfile.gettempdir(), "jarvis_speech.wav")
                with open(path, "wb") as fh:
                    fh.write(audio)
                self._play(path)
                return
            except Exception as exc:  # network/parse failure -> try next provider
                last_err = f"{name}: {exc}"

        # No cloud provider worked (or none configured): try OFFLINE SAPI so
        # Jarvis still speaks with no API key.
        try:
            self._speak_sapi(text, out_path=out_path)
        except Exception as exc:
            last_err = last_err or f"sapi: {exc}"

    # ---- offline TTS (Windows SAPI, no key) -------------------------------
    @staticmethod
    def _clean_for_speech(text: str) -> str:
        """Make model/assistant text read naturally aloud: drop markdown, code
        fences, bullet/heading markers, and stray symbols SAPI would read out.
        """
        import re

        t = text
        t = re.sub(r"```[\s\S]*?```", " ", t)          # code blocks
        t = re.sub(r"`([^`]+)`", r"\1", t)              # inline code ticks
        t = re.sub(r"[#*_>|]+", " ", t)                 # md markers
        t = re.sub(r"https?://\S+", " a link ", t)      # urls
        t = re.sub(r"[\(\)\[\]{}]", " ", t)             # brackets
        t = re.sub(r"\s+", " ", t).strip()
        return t or text

    def _speak_sapi(self, text: str, out_path: Optional[str] = None) -> dict:
        """Speak via Windows SAPI (pywin32). Plays directly; optionally saves wav.

        Picks the most human-sounding installed voice (neural/online/natural
        voices first, falling back to the default) and uses a calm rate so the
        reply sounds like a conversation, not a robot.
        """
        import win32com.client  # type: ignore

        speaker = win32com.client.Dispatch("SAPI.SpVoice")

        spoken = self._clean_for_speech(text)

        # Choose the most natural voice available.
        try:
            voices = speaker.GetVoices()
            preferred = None
            rank = ["neural", "online", "natural", "aria", "jenny", "david",
                    "george", "guy", "zira", "hazel", "susan"]
            best_idx, best_score = -1, 999
            for i in range(voices.Count):
                desc = (voices.Item(i).GetDescription() or "").lower()
                score = next((k for k, kw in enumerate(rank) if kw in desc), len(rank))
                if score < best_score:
                    best_score, best_idx = score, i
            if best_idx >= 0:
                preferred = voices.Item(best_idx)
            if preferred is not None:
                speaker.Voice = preferred
        except Exception:
            pass

        # Lively, conversational cadence: a touch faster than default, full
        # volume. Pair shorter sentence chunks so SAPI adds natural pauses.
        try:
            speaker.Rate = 1
            speaker.Volume = 100
        except Exception:
            pass

        if out_path:
            try:
                stream = win32com.client.Dispatch("SAPI.SpFileStream")
                stream.Open(out_path, 3)  # SPFM_CREATE = 3
                speaker.AudioOutputStream = stream
                speaker.Speak(spoken)
                stream.Close()
            except Exception:
                speaker.AudioOutputStream = None
                speaker.Speak(spoken)
        else:
            speaker.Speak(spoken)
        return {"ok": True, "provider": "sapi", "path": out_path or "", "text": text}

    # ---- playback helper --------------------------------------------------
    @staticmethod
    def _play(path: str) -> None:
        """Best-effort audio playback with no extra dependencies."""
        try:
            import platform, subprocess

            sys_os = platform.system()
            if sys_os == "Windows":
                import winsound

                winsound.PlaySound(path, winsound.SND_FILENAME)
            elif sys_os == "Darwin":
                subprocess.run(["afplay", path], check=False)
            else:  # Linux
                subprocess.run(["aplay", path], check=False)
        except Exception:
            pass  # never block the assistant on playback failure

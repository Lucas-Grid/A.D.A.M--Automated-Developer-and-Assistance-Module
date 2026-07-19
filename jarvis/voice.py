"""Voice output for Jarvis (folds ADAM's TTS in, dependency-light).

Strategy (no Piper binary / .onnx models required):
  * Primary: OpenAI-compatible TTS via NVIDIA NIM (nvidia/... speech models)
    using the same NVIDIA_NIM_API_KEY as the LLM. NIM exposes /v1/audio/speech.
  * Fallback: OpenAI TTS-1 if OPENAI_API_KEY is set.
  * If neither is available, speak() is a graceful no-op returning the text so
    the assistant still "responds" without audio.

Only stdlib + requests (already a project dependency). No audio playback
library is required — we save a .wav and return its path; the CLI can shell-open
it. This keeps the feature optional and crash-free on minimal installs.
"""
from __future__ import annotations

import base64
import json
import os
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

    def available(self) -> bool:
        return bool(self.nim_key or self.openai_key)

    def speak(self, text: str, out_path: Optional[str] = None) -> dict:
        """Synthesize ``text`` to speech. Returns a dict with status + path/b64.

        Never raises: on any failure or when no provider is configured, returns
        ok=False with the original text so callers can degrade gracefully.
        """
        import requests

        text = (text or "").strip()
        if not text:
            return {"ok": False, "error": "empty text", "text": text}

        providers = []
        if self.nim_key:
            providers.append(("nim", "https://integrate.api.nvidia.com/v1", self.nim_key, self.nim_model))
        if self.openai_key:
            providers.append(("openai", "https://api.openai.com/v1", self.openai_key, self.openai_model))

        if not providers:
            return {"ok": False, "error": "no TTS provider configured", "text": text}

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
                return {
                    "ok": True,
                    "provider": name,
                    "path": path,
                    "audio_base64": base64.b64encode(audio).decode("utf-8"),
                    "format": "audio/wav",
                    "text": text,
                }
            except Exception as exc:  # network/parse failure -> try next provider
                last_err = f"{name}: {exc}"
        return {"ok": False, "error": last_err or "all providers failed", "text": text}

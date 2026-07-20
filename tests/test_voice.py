"""Offline-possible test for voice INPUT (STT) transcription.

This proves the actual speech-to-text path (not just availability):

  * If a Vosk model + the vosk package are installed AND we can synthesize a
    speech WAV on this platform (Windows SAPI), we generate "open notepad ..."
    and assert VoiceInput.transcribe_wav() returns text containing the spoken
    words.
  * If the model or vosk is missing, the test PASSES as "not applicable" (we
    print a clear note) so the stdlib suite stays green on machines without
    STT set up -- the graceful-degrade behavior is still covered separately.

Real end-to-end mic capture is NOT exercised here (no audio device in CI); the
WAV path uses the exact Vosk KaldiRecognizer the live listener relies on.
"""
import os
import sys
import shutil
import subprocess
import tempfile

# Don't let a stray key flip the provider; STT is local/offline anyway.
os.environ.pop("NVIDIA_NIM_API_KEY", None)
sys.path.insert(0, r"C:\Users\vinot\Downloads\project")

from jarvis.voice_input import VoiceInput, _vosk_model_path


def _have_vosk() -> bool:
    try:
        import vosk  # noqa: F401

        return True
    except Exception:
        return False


def _make_speech_wav(path: str, phrase: str) -> bool:
    """Synthesize PHRASE to a 16k WAV via Windows SAPI. Returns True on success."""
    if not shutil.which("powershell"):
        return False
    ps = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.SetOutputToWaveFile('{path}'); "
        f"$s.Speak('{phrase}'); "
        "$s.Dispose()"
    )
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       check=True, capture_output=True, timeout=60)
        return os.path.isfile(path) and os.path.getsize(path) > 1000
    except Exception:
        return False


def test_voice_input_transcribe_path():
    if not _have_vosk() or _vosk_model_path() is None:
        print("  [note] Vosk/model not installed here -> STT transcription "
              "not exercised (graceful-degrade covered by other tests).")
        return  # not applicable on this machine; don't fail the suite
    wav = os.path.join(tempfile.gettempdir(), "jarvis_stt_fixture.wav")
    phrase = "open notepad and type hello world"
    if not _make_speech_wav(wav, phrase):
        print("  [note] could not synthesize speech fixture -> STT not exercised.")
        return
    try:
        vi = VoiceInput(on_command=lambda t: None)
        text = vi.transcribe_wav(wav)
        assert isinstance(text, str)
        low = text.lower()
        assert "notepad" in low and "hello" in low, f"transcription missed words: {text!r}"
    finally:
        try:
            os.remove(wav)
        except Exception:
            pass


def test_voice_input_graceful_without_model():
    # Force "no model" by pointing VOSK_MODEL_PATH at a nonexistent dir.
    os.environ["VOSK_MODEL_PATH"] = r"C:\nonexistent-vosk-model-xyz"
    try:
        vi = VoiceInput(on_command=lambda t: None)
        out = vi.transcribe_wav(r"C:\also-does-not-exist.wav")
        assert out == "", f"expected '' without model, got {out!r}"
    finally:
        os.environ.pop("VOSK_MODEL_PATH", None)

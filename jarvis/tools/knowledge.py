"""Knowledge tools: semantic memory + voice (folds ADAM's vector/voice in).

These are dependency-light wrappers over jarvis.vectormem.VectorMemory and
jarvis.voice.Voice. Both degrade gracefully when their backend (NIM embeddings
/ TTS) is unavailable, so they never crash a run.
"""
from __future__ import annotations

from typing import Any

from jarvis.tools.registry import Tool, ToolContext, ToolResult


def _vector(ctx: ToolContext) -> Any:
    vm = getattr(ctx, "vector", None)
    if vm is None:
        from jarvis.vectormem import VectorMemory

        vm = VectorMemory(db_path="jarvis_vector.db")
        ctx.vector = vm  # cache on the context for the session
    return vm


class SemanticRememberTool(Tool):
    name = "remember_semantic"
    description = "Store a fact/note in semantic memory (embedded for later similarity search). Returns the memory id."
    danger = "safe"
    schema = {
        "text": "string (required) - the text to remember",
        "collection": "string - namespace (default 'default')",
        "key": "string - optional stable id to upsert",
    }

    def run(self, ctx: ToolContext, text: str = "", collection: str = "default",
            key: str = "", **_: Any) -> ToolResult:
        if not text:
            return ToolResult(ok=False, output="", tool=self.name, error="text is required")
        try:
            cid = _vector(ctx).remember(text, collection=collection or "default", key=key or None)
            return ToolResult(ok=True, output=f"Remembered [{collection}] id={cid}", tool=self.name)
        except Exception as e:
            return ToolResult(ok=False, output="", tool=self.name, error=str(e))


class SemanticRecallTool(Tool):
    name = "recall_semantic"
    description = "Recall the most relevant past notes/facts by meaning (semantic search). Falls back to keyword match if embeddings are off."
    danger = "safe"
    schema = {
        "query": "string (required) - what to recall",
        "collection": "string - namespace (default 'default')",
        "top_k": "int - number of results (default 5)",
    }

    def run(self, ctx: ToolContext, query: str = "", collection: str = "default",
            top_k: int = 5, **_: Any) -> ToolResult:
        if not query:
            return ToolResult(ok=False, output="", tool=self.name, error="query is required")
        try:
            hits = _vector(ctx).recall(query, collection=collection or "default", top_k=max(1, int(top_k or 5)))
            if not hits:
                return ToolResult(ok=True, output="(no matching memories)", tool=self.name)
            out = []
            for h in hits:
                score = h.get("score", 0)
                out.append(f"[sim={score:.2f}] {h['text']}")
            return ToolResult(ok=True, output="\n".join(out), tool=self.name)
        except Exception as e:
            return ToolResult(ok=False, output="", tool=self.name, error=str(e))


class SpeakTool(Tool):
    name = "speak"
    description = "Read text aloud via TTS (NVIDIA NIM or OpenAI). No-op if no TTS provider is configured."
    danger = "safe"
    schema = {"text": "string (required) - what to say"}

    def run(self, ctx: ToolContext, text: str = "", **_: Any) -> ToolResult:
        if not text:
            return ToolResult(ok=False, output="", tool=self.name, error="text is required")
        try:
            from jarvis.voice import Voice

            voice = getattr(ctx, "voice", None) or Voice()
            ctx.voice = voice
            res = voice.speak(text)
            if res.get("ok"):
                return ToolResult(
                    ok=True,
                    output=f"[spoken via {res.get('provider')}] saved {res.get('path')}",
                    tool=self.name,
                )
            return ToolResult(
                ok=False,
                output=f"(TTS unavailable: {res.get('error')}) text: {text}",
                tool=self.name,
            )
        except Exception as e:
            return ToolResult(ok=False, output="", tool=self.name, error=str(e))

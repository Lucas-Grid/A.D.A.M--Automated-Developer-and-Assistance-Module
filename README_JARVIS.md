# Jarvis — Desktop-Centric Autonomous AI Assistant

A small, modular, dependency-light implementation of the "Desktop-Jarvis"
reference architecture: a multi-provider LLM router, a tool-calling agent
(orchestrator) that runs the plan → act → observe → answer loop, a sandboxed
code executor, and a short/long-term memory layer.

It runs **out of the box with no API key and no network** (a built-in
deterministic "local brain"), and you can plug in real LLM providers
(Ollama, OpenAI-compatible endpoints like Nous/OpenRouter/OpenAI, Anthropic)
via a config file. When the configured default provider is missing its API
key, Jarvis automatically falls back to the local brain at startup, so the
CLI, demo, and server always launch.

**Scope of the local (key-free) brain:** it can run Python in a sandbox, list
and read files, store/recall facts, and run web searches. It does **not** invent
free-form natural-language answers, and it has no branch for `edit_file`,
`run_shell`, or `build_project` — those tools require a real LLM provider
(NIM/Ollama). For full agentic coding ("build me an app"), configure a real
provider. The local brain is the offline smoke-test path, not the full product.

## Features
- **Multi-provider LLM routing** — local (key-free), Ollama, OpenAI-compatible.
- **Tool-calling agent loop** (MRKL/ReAct) — the model emits a JSON tool call,
  Jarvis executes it, feeds the result back, and repeats until done.
- **Real sandboxed tools** — Python/Shell execution (time-limited in-process,
  optional hardened Docker profile), file read/write/list, live web search,
  browser automation (Playwright, optional), persistent memory, guarded desktop
  automation (mouse/keyboard/screenshot), and a meta-agent that generates new
  tools from natural language.
- **Layered memory** (jarvis-ai-assistant pattern) — short / project / global
  scopes with tag-based fuzzy search; most-specific scope wins on recall.
- **Task side-channel + telemetry** (jarvis-ai-assistant / OpenJarvis patterns)
  — sub-tasks are tracked separately from the conversation context, and every
  step records latency/token cost via `ask_full()`.
- **Holographic GUI + voice control** — `python -m jarvis gui` boots a
  self-contained holographic HUD (canvas: rotating HUD rings + an interactive
  pulse that reacts to Jarvis' live state: idle / listening / thinking /
  speaking) served at `http://127.0.0.1:8000`. A WebSocket bridge streams state
  + transcript in real time. Optional voice input (wake word "Jarvis" or
  hands-free) routes speech straight into the assistant; a "hands-free" toggle
  auto-confirms desktop actions so you can drive the computer by voice.
- **Screen perception** — `screen_capture` / `screen_understand` OCR the real
  desktop (Tesseract) and optionally describe it via a vision-LLM, so Jarvis
  can *see* what's on screen.
- **Human-in-the-loop** — moderate/high-danger tools require confirmation in
  the CLI; the server runs auto-confirm but blocks nothing destructive by default.
- **Tool permissions + sandbox profiles (§3.1)** — every tool declares the
  permissions it needs (`fs.write`, `net`, …) and a sandbox profile
  (`none` / `inprocess` / `docker`) so the executor can gate and isolate it.
- **Model Selector / auto-routing (§4.2)** — weighted scoring of providers by
  cost, latency, and modality picks the best backend per request
  (`providers/selector.py`); exposed via `build_selector(cfg)`.
- **Provider response cache (§4.3)** — optional in-memory TTL cache memoises
  identical (model, prompt) generations, cutting calls + latency on paid
  endpoints; enable with `cache.ttl_seconds` in config.
- **YAML plugin system (§10)** — drop a `<name>.yaml` into `tools/plugins/` and
  it registers as a tool on startup, no core changes needed.
- **Two UIs** — interactive CLI REPL and a FastAPI HTTP service.

## What was harvested from the reference projects
These were studied and their useful patterns folded into `jarvis/` (no heavy
frameworks were adopted — the package stays dependency-light):
- **jarvis-ai-assistant (skyfireitdiy)** — layered tag-based memory (no vectors),
  task-list side-channel, method/rule loading, and the `meta_agent` tool
  self-generation (→ `tools/meta.py`).
- **OpenJarvis** — five composable primitives model, energy/cost telemetry
  (→ `memory.Telemetry`), offline-first design, and `ask_full()` returning
  content + tool_results + telemetry.
- **AutoGPT** — goal-driven loop-back planning (→ the orchestrator loop).
- **LangChain** — uniform provider/tool interfaces (→ `Tool` / `@tool`).
- **PyAutoGUI / Playwright** — desktop + browser automation (→ `tools/desktop.py`,
  `tools/browser.py`).
- **ADAM (Automated Developer & Assistance Module)** — semantic vector memory
  (embeddings via NVIDIA NIM `nvidia/nv-embed-v1`, SQLite + pure-Python cosine,
  no ChromaDB) and text-to-speech (→ `vectormem.py`, `voice.py`, and the
  `remember_semantic` / `recall_semantic` / `speak` tools).

## Quick start
```bash
cd project
pip install pyyaml requests fastapi uvicorn   # (system Python 3.11 already has these)
python -m jarvis.demo          # end-to-end demo, no keys needed
python -m jarvis.cli            # interactive REPL: jarvis> run this python: print(2**10)
python -m jarvis.server         # HTTP API on http://127.0.0.1:8000
```

The server exposes:
- `GET  /health` — status + active provider
- `GET  /tools`  — list registered tools (with declared permissions + sandbox profile)
- `GET  /memory?key=...&scope=...` — recall a stored fact (or all memories)
- `POST /ask`     — `{"message": "..."}` → `{"answer": "..."}`
- `POST /ask_full` — same, plus `tool_results`, `telemetry`, and `tasks`
- `POST /recall_semantic` — `{"query": "...", "collection": "...", "top_k": 5}` → semantic memory hits
- `POST /speak`   — `{"text": "..."}` → TTS audio (NIM/OpenAI) or graceful no-op

Plugins in `tools/plugins/*.yaml` are loaded automatically and appear in `/tools`.

```bash
curl -s -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json" \
  -d '{"message":"run this python: print(2**10)"}'
```

## Configuration (`.jarvis.yaml`)
Copy `jarvis/.jarvis.example.yaml` to `.jarvis.yaml` and edit. The `local`
provider is always available. To use a real model, uncomment a block:

```yaml
providers:
  - name: nim                 # NVIDIA NIM — main provider (OpenAI-compatible)
    type: nous
    model: stepfun-ai/step-3.7-flash   # fast; or openai/gpt-oss-120b for max capability
    base_url: https://integrate.api.nvidia.com/v1
    api_key: env:NVIDIA_NIM_API_KEY     # read from env, never stored in the file
    enabled: true
  - name: ollama
    type: ollama
    model: qwen3:8b
    base_url: http://localhost:11434
  - name: openrouter
    type: openai_compat
    vendor: openrouter
    model: meta-llama/llama-3.1-8b-instruct
    base_url: https://openrouter.ai/api/v1
    api_key: ${OPENROUTER_API_KEY}
default_provider: nim
```

When a real provider is the `default_provider`, Jarvis prompts it with the tool
catalogue and expects the same `{"tool": ..., "args": ...}` JSON envelope the
local provider emits.

## Architecture
```
jarvis/
  config.py            # YAML config (no PyYAML required; uses stdlib fallback)
  types.py             # Message, GenerationResult, ToolResult, Action
  providers/
    base.py            # LLMProvider interface
    local.py           # deterministic key-free brain (default)
    ollama.py          # local models via /api/chat
    openai_compat.py   # OpenAI / OpenRouter / Nous / Anthropic-compatible
    registry.py        # build_providers / get_provider
  tools/
    registry.py        # Tool protocol + ToolRegistry + @tool decorator
    sandbox.py         # SandboxExecutor (time-limited / Docker)
    files.py           # file_list / file_read / file_write
    builtins.py        # web_search / memory_store / memory_recall (scoped + tagged)
    coding.py          # edit_file (creates or edits files) / run_shell / run_tests / init_project
    builder.py         # build_project (Phase C: prompt -> scaffold -> code -> test -> commit)
    desktop.py         # desktop_click/type/move/hotkey + screen_capture/understand (guarded)
    knowledge.py       # remember_semantic / recall_semantic / speak (folds in ADAM)
    browser.py         # browser (Playwright, optional)
    meta.py            # meta_create_tool (generates + registers new tools live)
    plugins.py         # YAML plugin loader
  vectormem.py         # semantic memory (SQLite + NIM embeddings + cosine; no ChromaDB)
  voice.py             # text-to-speech via NIM/OpenAI (graceful no-op)
  memory.py            # layered SQLite store (short/project/global + tags) + TaskList + Telemetry
  orchestrator.py      # the agent loop + ask_full() (content/tool_results/telemetry/tasks)
  cli.py               # interactive REPL
  server.py            # FastAPI service
  gui.py               # holographic HUD server (WS + voice bridge)
  gui/holo.html        # self-contained canvas HUD (pulse rings, transcript)
  voice_input.py       # optional STT: wake-word + hands-free (vosk/SR)
  demo.py              # end-to-end smoke test
```

## Holographic GUI & voice control
```bash
python -m jarvis gui            # opens the holographic HUD at http://127.0.0.1:8000
```
The HUD is a self-contained `jarvis/gui/holo.html` (no build step, no CDN): a
rotating circular HUD with concentric **interactive pulse** rings that change
color and motion with Jarvis' live state. In the browser, use the **Mic** and
**Hands-free** buttons:

- **Mic on** starts voice input (wake word "Jarvis", then your command; or
  hands-free continuous mode). Recognized speech is routed into the assistant
  and the HUD shows it.
- **Hands-free on** auto-confirms desktop actions (clicks / typing / app
  launches) so you can operate the computer entirely by voice. Leave it off to
  keep the CLI-style confirmation gate.

Voice input is **optional**. Install one backend (Jarvis runs fine without it):
- Offline (recommended, no API key): `pip install vosk` + download a model
  from https://alphacephei.com/vosk/models, then set `VOSK_MODEL_PATH`.
- Online: `pip install SpeechRecognition pyaudio` (uses Google STT).

Computer control (mouse, keyboard, clicks, app launch) is already wired via
`pyautogui` (`desktop_click`, `desktop_type`, `desktop_move`, `desktop_hotkey`,
`app_launch`). Screen perception is `screen_capture` / `screen_understand`.

## Security model
- Generated code runs time-limited (10s) and with a restricted builtins set by
  default. Set `sandbox.use_docker: true` to run it inside a disposable,
  network-isolated, resource-limited container (requires Docker).
- `desktop_click` / `desktop_type` are `high` danger and always require explicit
  confirmation; they are no-ops without `pyautogui` installed.
- Memory and files are scoped to the configured `workspace`.

## Adding a tool (plugin system)
```python
from jarvis.tools.registry import tool, ToolResult

@tool("my_tool", description="Does a thing", danger="safe")
def my_tool(ctx, arg: str = "") -> ToolResult:
    return ToolResult(ok=True, output=f"did {arg}", tool="my_tool")
```
No core changes needed — it is automatically registered and discoverable by the
provider via the tool catalogue.

## Testing
The suite is pure-stdlib (no pytest needed) and lives in `tests/` with a small
discovering runner.

```bash
python tests/run_tests.py            # run everything (offline)
python tests/run_tests.py editfile    # run one module (file stem, e.g. editfile/tools/memory)
python tests/run_tests.py -v          # verbose per-test output
```
From the CLI REPL, type `test` to run the same suite.

Offline tests cover every tool's `run()` path, `edit_file` (create/edit/decline),
the layered + semantic memory stores, config parsing, provider selection, the
orchestrator agent loop, and the FastAPI server wiring.

A live smoke test (`tests/test_live.py`) exercises real reasoning, code
execution, and cross-turn memory on NVIDIA NIM. It auto-skips unless
`NVIDIA_NIM_API_KEY` is set:

```bash
NVIDIA_NIM_API_KEY=... python tests/run_tests.py live
```

## Notes on the environment
This project deliberately registers FastAPI routes directly on the `FastAPI`
app rather than via a shared `APIRouter`, because the installed FastAPI
0.138.2 / Starlette 1.3.1 combo drops routes when `include_router` is used
(verified with a minimal repro). If you upgrade FastAPI, you can switch back to
router-based wiring.

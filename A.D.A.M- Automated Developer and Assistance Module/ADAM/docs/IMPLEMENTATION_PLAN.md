# ADAM OS Implementation Plan

## Phase 0 — Foundation (Current)

Goal: stable backend foundation only. No UI, no voice, no multi-agent orchestration.

### Completed Tasks

1. **Project scaffolding** — Folder structure, README, pyproject, requirements, .gitignore.
2. **Core app** — `core/app.py`, `core/config.py`, `core/events.py`, `core/exceptions.py`, `core/types.py`, `core/database.py`.
3. **Memory Store** — SQLite-backed key-value store with tag search.
4. **Skill Engine** — `BaseSkill` ABC, `SkillRegistry`, `SkillEngine` with discovery, loading, async execution.
5. **PowerShell Connector** — Subprocess-based runner with safety guards (`-NonInteractive`, blocked patterns).
6. **Ollama Client** — Minimal HTTP wrapper for local inference.
7. **Project Registry** — CRUD for AI project metadata.
8. **API v1** — FastAPI routers for `/registry`, `/skills`, `/system`.
9. **Tests** — Minimal pytest suite covering memory, skills, registry, PowerShell.
10. **Config** — YAML configs + `.env.example` schema.

### Next Steps (Out of Scope for Foundation)

- Phase 1: Agent runtime & execution sandbox
- Phase 2: Workspace filesystem indexer + watcher
- Phase 3: AI Ops (embedding pipeline, ChromaDB-style vector store)
- Phase 4: Automation scheduler + trigger system
- Phase 5: Multi-agent UI (PySide6 desktop client)

## Folder Tree

```
ADAM/
├── __init__.py
├── main.py
├── pyproject.toml
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── core/
│   ├── __init__.py
│   ├── app.py
│   ├── config.py
│   ├── database.py
│   ├── events.py
│   ├── exceptions.py
│   ├── registry.py
│   └── types.py
├── memory/
│   ├── __init__.py
│   └── store.py
├── skills/
│   ├── __init__.py
│   ├── base.py
│   ├── engine.py
│   ├── registry.py
│   └── builtins/
│       ├── __init__.py
│       └── system.py
├── connections/
│   ├── __init__.py
│   ├── ollama.py
│   └── powershell.py
├── agents/
│   └── __init__.py
├── automations/
│   └── __init__.py
├── workspace/
│   └── __init__.py
├── api/
│   ├── __init__.py
│   └── v1/
│       ├── __init__.py
│       ├── router.py
│       ├── registry.py
│       ├── skills.py
│       └── system.py
├── data/
│   └── .gitkeep
├── logs/
│   └── .gitkeep
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_memory.py
│   ├── test_powershell.py
│   ├── test_registry.py
│   └── test_skills.py
└── config/
    ├── logging.yaml
    ├── settings.yaml
    └── skills.yaml
```

## Startup Flow

1. `python main.py` calls `create_app()`
2. `create_app()` loads `Settings` (from `.env` + `config/settings.yaml` + defaults)
3. Ensures `data/`, `logs/`, and `data/workspace/` directories exist
4. Registers CORS, startup and shutdown events
5. Includes `/api/v1` router
6. Uvicorn starts on `127.0.0.1:8000`
7. On first request to any endpoint, singleton services resolve:
   - `ProjectRegistry` → ensures `projects` table exists
   - `MemoryStore` → ensures `memory` and `memory_index` tables exist
   - `SkillEngine` → discovers built-in skills and registers them
8. Endpoints delegate to these services

## Build Report

**Date:** 2026-06-22  
**Phase:** 0 — Foundation  
**Status:** Complete

### Deliverables
- 32 files created
- 4 core backend services implemented
- 7 API endpoints exposed
- 4 unit-test modules scaffolded
- Documentation: architecture, implementation plan, this report

### Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| SQLite WAL mode on Windows file sharing | Use local-only paths in development; future phase enables proper locking |
| PowerShell execution safety | Disallowed interactive patterns; scoped to `workspace_dir` |
| Unbounded memory growth | Future: TTL + embedding deduplication in Phase 3 |

### Verification

- [x] Folder structure matches spec
- [x] Python modules are importable (pending pytest run in verification step)
- [x] No UI, voice, or orchestration code introduced
- [x] Commit message: `feat(foundation): initial ADAM OS backend scaffold`

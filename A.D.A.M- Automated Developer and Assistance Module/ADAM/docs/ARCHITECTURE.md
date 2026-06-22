# ADAM OS Architecture

## 1. Design Principles

- **Modular over monolithic:** Each domain lives under its own package (`memory`, `skills`, `connections`, etc.).
- **Singleton accessors:** Shared services (`get_settings`, `get_memory`, `get_skill_engine`, `get_project_registry`) are lazily initialized singletons accessed via dependency-like functions.
- **SQLite-first persistence:** `data/adam.db` is the single source of truth for structured state. WAL mode is enabled for concurrent reads.
- **Subprocess isolation:** PowerShell and future external tools are executed via `subprocess.run` with strict whitelisting and non-interactive flags.
- **Future-proof API:** FastAPI provides OpenAPI docs and typed endpoints from day one; the PySide6 desktop client will consume the same `/api/v1` surface.

## 2. Package Map

| Package | Responsibility |
|---------|----------------|
| `core/` | App factory, config, DB engine, exceptions, shared types |
| `memory/` | Key-value memory store with tag support and search |
| `skills/` | Base skill interface, registry, engine, discovery |
| `agents/` | Reserved for Phase 2+ (multi-agent orchestration) |
| `connections/` | PowerShell + Ollama adapters |
| `automations/` | Reserved for automation triggers and runners |
| `workspace/` | Reserved for filesystem indexing and project watchers |
| `api/v1/` | FastAPI routers: registry, skills, system |
| `data/` | SQLite DB, workspace file storage |
| `logs/` | Runtime log files |
| `tests/` | pytest suite |
| `config/` | YAML + env configuration sources |

## 3. Data Flow

1. `main.py` starts the uvicorn server → `create_app()`
2. Startup event logs boot info; routes become available under `/api/v1/`
3. Each endpoint delegates to a service layer (e.g., `ProjectRegistry`, `MemoryStore`, `SkillEngine`)
4. Service layer reads/writes SQLite directly (no ORM complexity for foundation phase)
5. External binaries (PowerShell, Ollama) go through `connections.*` wrapper classes

## 4. Security Constraints

- PowerShell execution: `-NoProfile -NonInteractive -ExecutionPolicy Bypass`
- Blocked patterns: `Read-Host`, `Get-Credential`
- Workspace filesystem scope is intentionally restricted in this foundation phase

## 5. Windows-First Decisions

- SQLite WAL mode for file locking compatibility
- PowerShell as default shell integration due to deep Windows 11 system API coverage
- ASCII-only paths recommended in project root to avoid `pathlib` issues with PySide6 (future)

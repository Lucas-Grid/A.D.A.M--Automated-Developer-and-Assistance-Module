# ADAM OS

**ADAM is not a chatbot. ADAM is an operating system for AI.**

This repository contains the backend foundation for ADAM OS — a modular, Windows-first AI Operating System built on Python 3.12+, FastAPI, and SQLite.

## Status: Foundation Complete

Backend services implemented:
- Project Registry
- Memory Store
- Skill Engine
- PowerShell Connector

## Quick Start

```bash
cd ADAM
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python main.py
```

API will be available at `http://127.0.0.1:8000/api/v1`.

## Documentation

See `docs/` for architecture, implementation plan, and build report.

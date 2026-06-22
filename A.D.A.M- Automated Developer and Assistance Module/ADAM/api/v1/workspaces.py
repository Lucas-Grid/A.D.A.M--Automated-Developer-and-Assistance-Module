"""Workspace API endpoints."""
from fastapi import APIRouter, HTTPException

from ADAM.core.types import ResponseModel
from ADAM.workspace.analyzer import ProjectAnalyzer
from ADAM.workspace.manager import get_workspace_manager
from ADAM.workspace.memory import WorkspaceMemory

router = APIRouter()


@router.post("/", response_model=ResponseModel)
def register_workspace(name: str, path: str, description: str = ""):
    try:
        ws = get_workspace_manager().register(name, path, description)
        return ResponseModel(ok=True, data=ws)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/", response_model=ResponseModel)
def list_workspaces():
    return ResponseModel(ok=True, data=get_workspace_manager().list_workspaces())


@router.get("/active", response_model=ResponseModel)
def get_active_workspace():
    ws = get_workspace_manager().get_active()
    return ResponseModel(ok=True, data=ws)


@router.post("/active/{name}", response_model=ResponseModel)
def set_active_workspace(name: str):
    try:
        ws = get_workspace_manager().set_active(name)
        return ResponseModel(ok=True, data=ws)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/scan", response_model=ResponseModel)
def scan_workspace(path: str):
    try:
        scanner = ProjectAnalyzer()
        result = scanner.analyze(path)
        return ResponseModel(ok=True, data=result)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/analyze", response_model=ResponseModel)
def analyze_workspace(path: str):
    try:
        analyzer = ProjectAnalyzer()
        result = analyzer.analyze(path)
        return ResponseModel(ok=True, data=result)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/memory/current", response_model=ResponseModel)
def get_workspace_memory():
    return ResponseModel(ok=True, data=WorkspaceMemory().load_current())

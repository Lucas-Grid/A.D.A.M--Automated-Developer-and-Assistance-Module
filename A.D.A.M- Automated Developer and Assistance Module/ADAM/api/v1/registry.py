"""Project registry API endpoints."""
from fastapi import APIRouter, HTTPException

from ADAM.core.types import ResponseModel
from ADAM.core.registry import get_project_registry

router = APIRouter()


@router.post("/projects", response_model=ResponseModel)
def create_project(name: str, path: str, description: str = "", model_tag: str = ""):
    try:
        project = get_project_registry().create(name, path, description, model_tag)
        return ResponseModel(ok=True, data=project)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/projects", response_model=ResponseModel)
def list_projects():
    projects = get_project_registry().list_projects()
    return ResponseModel(ok=True, data=projects)


@router.get("/projects/{name}", response_model=ResponseModel)
def get_project(name: str):
    project = get_project_registry().get(name)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ResponseModel(ok=True, data=project)


@router.delete("/projects/{name}", response_model=ResponseModel)
def delete_project(name: str):
    get_project_registry().delete(name)
    return ResponseModel(ok=True, data={"deleted": name})

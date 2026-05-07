"""Projects routes. Replaces backend/src/routes/projects.ts."""

from fastapi import APIRouter, Depends, Request, HTTPException
from app.auth.middleware import require_auth
from app.db.connection import get_pool
from app.db.models import list_projects, create_project, get_project

router = APIRouter()


@router.get("/")
async def get_projects(request: Request, _=Depends(require_auth)):
    db = await get_pool()
    return await list_projects(db, request.state.user_id)


@router.post("/")
async def new_project(request: Request, _=Depends(require_auth)):
    body = await request.json()
    db = await get_pool()
    return await create_project(
        db, request.state.user_id, body["name"],
        cm_number=body.get("cm_number"),
        visibility=body.get("visibility", "private"),
    )


@router.get("/{project_id}")
async def get_project_detail(project_id: str, request: Request, _=Depends(require_auth)):
    db = await get_pool()
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

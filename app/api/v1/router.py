from fastapi import APIRouter

from app.api.v1 import auth, labels, orgs, projects, tasks, users

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(labels.router)
router.include_router(orgs.router)
router.include_router(projects.router)
router.include_router(tasks.router)
router.include_router(users.router)

from fastapi import APIRouter

from app.api.v1 import auth, orgs, users

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(orgs.router)
router.include_router(users.router)

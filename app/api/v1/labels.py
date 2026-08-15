import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_org_role
from app.db.session import get_db
from app.models.org_member import OrgMember, OrgRole
from app.schemas.label import LabelCreate, LabelPublic
from app.services.label_service import DuplicateLabelNameError, create_label, list_labels

router = APIRouter(prefix="/orgs/{org_id}/labels", tags=["labels"])


@router.post("", response_model=LabelPublic, status_code=status.HTTP_201_CREATED)
async def create_label_endpoint(
    org_id: uuid.UUID,
    body: LabelCreate,
    db: AsyncSession = Depends(get_db),
    _membership: OrgMember = Depends(require_org_role(OrgRole.MEMBER)),
) -> LabelPublic:
    try:
        label = await create_label(db, org_id=org_id, name=body.name, color=body.color)
    except DuplicateLabelNameError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A label with that name already exists in this org",
        ) from exc
    return LabelPublic.model_validate(label)


@router.get("", response_model=list[LabelPublic])
async def list_labels_endpoint(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership: OrgMember = Depends(require_org_role(OrgRole.MEMBER)),
) -> list[LabelPublic]:
    labels = await list_labels(db, org_id=org_id)
    return [LabelPublic.model_validate(label) for label in labels]

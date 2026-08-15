import enum
import uuid

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OrgRole(enum.StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"


class OrgMember(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Links a user to an org with a role. created_at doubles as joined_at."""

    __tablename__ = "org_members"
    __table_args__ = (UniqueConstraint("org_id", "user_id", name="uq_org_members_org_user"),)

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[OrgRole] = mapped_column(
        Enum(
            OrgRole,
            name="org_role",
            native_enum=True,
            # Without this, SQLAlchemy sends the Python member NAME ("OWNER")
            # instead of its VALUE ("owner") — but the Postgres enum type was
            # created with lowercase values in the migration, so they'd mismatch.
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=OrgRole.MEMBER,
        nullable=False,
    )

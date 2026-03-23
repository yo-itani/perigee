from sqlalchemy import CHAR, VARCHAR, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from foundation.db.base import Base, TimestampMixin


class WorkspaceTable(Base, TimestampMixin):
    """ORM model for the workspaces table."""

    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(
        CHAR(36),
        ForeignKey("workspaces.id", ondelete="RESTRICT"),
        nullable=True,
    )

    memberships: Mapped[list["MembershipTable"]] = relationship(
        back_populates="workspace",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class MembershipTable(Base, TimestampMixin):
    """ORM model for the memberships table."""

    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "user_id", name="uq_memberships_workspace_user"
        ),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)

    workspace: Mapped["WorkspaceTable"] = relationship(
        back_populates="memberships",
    )

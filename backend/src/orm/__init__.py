"""ORM model definitions split by domain.

Import from `backend.orm` for ORM model classes.
Backward-compatible: `from core.infra.database import X` also works.
"""

from core.base import Base

# Import from domain files
from orm.auth import RefreshTokenDB, RoleDB, UserDB, UserRoleDB
from orm.content import PromptDB, VersionDB
from orm.key import KeyUsageLog, UserApiKey
from orm.session import ChatMessage, MemoryEntry, ProjectRun, SessionDB
from orm.team import AttachmentDB, AuditLogDB, CommandLogDB

__all__ = [
    "Base",
    "AttachmentDB",
    "AuditLogDB",
    "ChatMessage",
    "CommandLogDB",
    "KeyUsageLog",
    "MemoryEntry",
    "ProjectRun",
    "PromptDB",
    "RefreshTokenDB",
    "RoleDB",
    "SessionDB",
    "UserApiKey",
    "UserDB",
    "UserRoleDB",
    "VersionDB",
]

"""ORM model definitions split by domain.

Import from `backend.orm` for ORM model classes.
Backward-compatible: `from core.infra.database import X` also works.
"""

from core.base import Base

# Import from domain files
from orm.auth import RefreshTokenDB, RoleDB, UserDB, UserRoleDB
from orm.infra import AssetDB, AttachmentDB, AuditLogDB, CommandLogDB
from orm.key import KeyUsageLog, UserApiKey
from orm.prompt_db import PromptDB, VersionDB
from orm.session import ChatMessage, MemoryEntry, ProjectRun, SessionDB

__all__ = [
    "Base",
    "AssetDB",
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

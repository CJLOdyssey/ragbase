"""One-time migration: remove builtin tools from the database.

Run: cd backend && PYTHONPATH=src python ../scripts/remove_builtin_tools.py
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "src"))

from sqlalchemy import select

from core.infra.database import get_session_factory
from orm.agent import AgentConfigDB
from orm.content import RegisteredSkillDB, RegisteredToolDB

BUILTIN_TOOLS = {
    "web_search", "fetch_page", "calculator",
    "execute_python", "open_user_browser",
}


async def main() -> None:
    factory = get_session_factory()
    async with factory() as session:
        # 1) Delete builtin tool rows
        rows = (await session.execute(
            select(RegisteredToolDB).where(RegisteredToolDB.is_builtin == True)
        )).scalars().all()
        for r in rows:
            await session.delete(r)
        print(f"deleted {len(rows)} builtin tool rows")

        # 2) Clean agent tools JSON bindings
        agents = (await session.execute(select(AgentConfigDB))).scalars().all()
        cleaned_agents = 0
        for a in agents:
            if not a.tools:
                continue
            try:
                items = json.loads(a.tools)
            except Exception:
                continue
            if not isinstance(items, list):
                continue
            filtered = [
                t for t in items
                if isinstance(t, dict) and t.get("name") not in BUILTIN_TOOLS
            ]
            if len(filtered) != len(items):
                a.tools = json.dumps(filtered, ensure_ascii=False)
                cleaned_agents += 1
        print(f"cleaned {cleaned_agents} agent tool bindings")

        # 3) Clean skill tool_names
        skills = (await session.execute(select(RegisteredSkillDB))).scalars().all()
        cleaned_skills = 0
        for s in skills:
            if not isinstance(s.tool_names, list):
                continue
            filtered = [t for t in s.tool_names if t not in BUILTIN_TOOLS]
            if len(filtered) != len(s.tool_names):
                s.tool_names = filtered
                cleaned_skills += 1
        print(f"cleaned {cleaned_skills} skill tool_names")

        await session.commit()
        print("migration done")


if __name__ == "__main__":
    asyncio.run(main())

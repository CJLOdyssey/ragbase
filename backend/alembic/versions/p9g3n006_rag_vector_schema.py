"""RAG P0: normalize vector_chunks for enterprise isolation and hybrid search.

Adds user_id (mandatory isolation key), asset_id (per-asset lifecycle) and
metadata (JSONB) columns; enables pg_trgm for the lexical retrieval leg
(trigram similarity, GIN-indexed) alongside the existing pgvector HNSW leg.

SQLite (dev/test fallback) is a no-op — rag_store._ensure_table creates the
runtime table there; the canonical schema lives in this migration for Postgres.
"""

from alembic import op

revision = "p9g3n006"
down_revision = "p9g3n005"
branch_labels = None
depends_on = None

_FULL_SCHEMA = """
CREATE TABLE IF NOT EXISTS vector_chunks (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    run_id TEXT,
    text TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    embedding vector(1024),
    user_id TEXT NOT NULL DEFAULT '',
    asset_id TEXT,
    metadata JSONB
)
"""


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(_FULL_SCHEMA)

    # Pre-existing tables (created by the legacy runtime _ensure_table) need
    # the new columns added on top.
    op.execute("ALTER TABLE vector_chunks ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT ''")
    op.execute("ALTER TABLE vector_chunks ADD COLUMN IF NOT EXISTS asset_id TEXT")
    op.execute("ALTER TABLE vector_chunks ADD COLUMN IF NOT EXISTS metadata JSONB")

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_vector_chunks_text_trgm "
        "ON vector_chunks USING gin (text gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_vector_chunks_asset_id "
        "ON vector_chunks (asset_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_vector_chunks_user_id "
        "ON vector_chunks (user_id)"
    )

    # Legacy assets were indexed with session_id = 'asset:{id}'; recover the
    # asset linkage so delete-cascade and per-asset reindex work on old data.
    op.execute(
        "UPDATE vector_chunks SET asset_id = substr(session_id, 7) "
        "WHERE session_id LIKE 'asset:%'"
    )
    # Legacy conversation-memory chunks have no owner; keep them visible only
    # to the anonymous/system path instead of leaking across users.
    op.execute("UPDATE vector_chunks SET user_id = 'anonymous' WHERE user_id = ''")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("DROP INDEX IF EXISTS idx_vector_chunks_user_id")
    op.execute("DROP INDEX IF EXISTS idx_vector_chunks_asset_id")
    op.execute("DROP INDEX IF EXISTS idx_vector_chunks_text_trgm")
    op.drop_column("vector_chunks", "metadata")
    op.drop_column("vector_chunks", "asset_id")
    op.drop_column("vector_chunks", "user_id")

"""Asset source columns — multi-source readiness (A: URL import; B/C reserved for connectors)."""

import sqlalchemy as sa
from alembic import op

revision = "p9g3n012"
down_revision = "p9g3n011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assets",
        sa.Column(
            "source",
            sa.String(16),
            nullable=False,
            server_default="upload",
            comment="upload | url — B/C reserved: sharepoint, s3, db, dir",
        ),
    )
    op.add_column(
        "assets",
        sa.Column(
            "source_ref",
            sa.Text(),
            nullable=True,
            comment="URL for source=url; connector-native ref for B/C sources",
        ),
    )


def downgrade() -> None:
    op.drop_column("assets", "source_ref")
    op.drop_column("assets", "source")

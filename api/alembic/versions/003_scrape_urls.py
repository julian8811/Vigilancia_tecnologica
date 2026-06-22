"""Add scrape_urls to search_strategies.

Revision ID: 003_scrape_urls
Revises: 002_collection_runs
Create Date: 2026-06-20 03:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_scrape_urls"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "search_strategies",
        sa.Column("scrape_urls", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("search_strategies", "scrape_urls")

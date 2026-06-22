"""Add error_message to reports.

Revision ID: 004_report_error_message
Revises: 003_scrape_urls
Create Date: 2026-06-20 05:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_report_error_message"
down_revision: Union[str, None] = "003_scrape_urls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("reports", "error_message")

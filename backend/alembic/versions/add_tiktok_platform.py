"""add tiktok to platform enum

Revision ID: add_tiktok_platform
Revises: # b259e80586bd
Create Date: 2026-03-26
"""
from alembic import op

revision = 'add_tiktok_platform'
down_revision = 'b259e80586bd'  # replace with your current head
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE platform ADD VALUE IF NOT EXISTS 'tiktok'")


def downgrade():
    # PostgreSQL doesn't support removing enum values — leave empty
    pass
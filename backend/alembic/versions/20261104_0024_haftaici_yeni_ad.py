"""hafta içi mutfağının adı: "Hızlı ama Lezzetli Yemekler"

Revision ID: 0024
Revises: 0023
"""
from collections.abc import Sequence

from alembic import op

revision: str = '0024'
down_revision: str | None = '0023'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE cuisines SET name = 'Hızlı ama Lezzetli Yemekler' WHERE slug = 'haftaici'")


def downgrade() -> None:
    op.execute("UPDATE cuisines SET name = 'Hafta İçi Yemekleri' WHERE slug = 'haftaici'")

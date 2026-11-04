"""'Hafta İçi Yemekleri' mutfağının adı 'Hızlı ama lezzetli yemekler' olur (slug aynı kalır)

Revision ID: 0024
Revises: 0023
Create Date: 2026-11-04 19:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0024'
down_revision: str | None = '0023'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("UPDATE cuisines SET name = 'Hızlı ama lezzetli yemekler' WHERE slug = 'haftaici'"))


def downgrade() -> None:
    op.execute(sa.text("UPDATE cuisines SET name = 'Hafta İçi Yemekleri' WHERE slug = 'haftaici'"))

"""tariflerin adımlarına süre eklenir: pişirme modundaki sayaç artık tariflerin çoğunda çıkar

Sayaç, adım metninde "15 dakika" gibi bir süre yazıyorsa kurulur; 249 tarifin yalnız 33'ünde yazıyordu.
Süreler alembic/recipe_data/sureler.py içindedir; yalnız belirtilen adımlar değişir, tarifin kalanı aynı kalır.
Yeni tarif ve eski (0011-0015) ilk tarifler bu göçte yoktur.

Revision ID: 0025
Revises: 0024
Create Date: 2026-11-05 20:00:00

"""
import sys
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from recipe_data.hafta_ici import HAFTA_ICI  # noqa: E402
from recipe_data.sureler import SURELER  # noqa: E402
from recipe_data.turk_ana import ANA  # noqa: E402
from recipe_data.turk_ek import EK  # noqa: E402
from recipe_data.world import ASYA, ITALYAN, MEKSIKA  # noqa: E402

revision: str = '0025'
down_revision: str | None = '0024'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ORIGINAL = {r["slug"]: r["steps"] for data in (ANA, EK, ITALYAN, ASYA, MEKSIKA, HAFTA_ICI) for r in data}


def _apply(changes: dict[str, dict[int, str]], expect: dict[str, dict[int, str]]) -> None:
    """Adımı yalnız beklenen metinde ise değiştirir (elle düzenlenmiş adımın üstüne yazmaz)."""
    conn = op.get_bind()
    for slug, steps in changes.items():
        row = conn.execute(sa.text("SELECT id, steps FROM recipes WHERE slug = :s"), {"s": slug}).first()
        if row is None:
            continue
        lines = row.steps.split("\n")
        for idx, text in steps.items():
            if idx < len(lines) and lines[idx] == expect[slug][idx]:
                lines[idx] = text
        conn.execute(sa.text("UPDATE recipes SET steps = :t WHERE id = :i"), {"t": "\n".join(lines), "i": row.id})


def upgrade() -> None:
    _apply(SURELER, {slug: {i: ORIGINAL[slug][i] for i in steps} for slug, steps in SURELER.items()})


def downgrade() -> None:
    _apply(
        {slug: {i: ORIGINAL[slug][i] for i in steps} for slug, steps in SURELER.items()},
        SURELER,
    )

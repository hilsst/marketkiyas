"""flexible meal plans: 1-14 days, weekday choice, budget, leftovers, low-waste, pantry ("dolabımda ne var")

- meal_plans.days: plan kaç gün (1-14). Eski planlar: günlük 1, haftalık 7. period artık bilgi amaçlı
  (daily / weekly / custom).
- meal_plans.weekdays: yemek yapılacak haftanın günleri (0 = Pazartesi, virgülle); boş = her gün.
- meal_plans.budget: plan için TL bütçe hedefi (alışveriş tutarı); boş = sınırsız.
- meal_plans.leftovers: "bir pişir iki ye" (akşam yemeği iki kat pişer, ertesi gün öğlene kalır).
- meal_plans.low_waste: malzemesi ortak tarifler öne çıkar (paketler boşa gitmesin).
- meal_plans.have_items: kullanıcının evde olduğunu söylediği malzemeler ("|" ile); maliyete ve listeye
  girmez, bu malzemeleri kullanan tarifler öne çıkar.
- meal_plan_entries.leftover_of_id: bu yemek, o kaydın kalanı (ayrıca pişirilmez).

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-31 22:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0016'
down_revision: str | None = '0015'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('meal_plans', sa.Column('days', sa.Integer(), server_default='7', nullable=False))
    op.execute("UPDATE meal_plans SET days = CASE WHEN period = 'daily' THEN 1 ELSE 7 END")
    op.add_column('meal_plans', sa.Column('weekdays', sa.String(length=16), server_default='', nullable=False))
    op.add_column('meal_plans', sa.Column('budget', sa.Numeric(10, 2), nullable=True))
    op.add_column('meal_plans', sa.Column('leftovers', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('meal_plans', sa.Column('low_waste', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('meal_plans', sa.Column('have_items', sa.Text(), server_default='', nullable=False))
    op.add_column('meal_plan_entries', sa.Column('leftover_of_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_meal_plan_entries_leftover_of', 'meal_plan_entries', 'meal_plan_entries',
        ['leftover_of_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_meal_plan_entries_leftover_of', 'meal_plan_entries', type_='foreignkey')
    op.drop_column('meal_plan_entries', 'leftover_of_id')
    for col in ('have_items', 'low_waste', 'leftovers', 'budget', 'weekdays', 'days'):
        op.drop_column('meal_plans', col)

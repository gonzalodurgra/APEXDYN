"""add_fuel_tank_capacity_and_bsfc

Revision ID: b749d1134a91
Revises: ee1328093dd5
Create Date: 2026-11-03 21:12:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b749d1134a91'
down_revision: Union[str, Sequence[str], None] = 'ee1328093dd5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('vehicles', sa.Column('fuel_tank_capacity_l', sa.Float(), nullable=True))
    op.add_column('engines', sa.Column('bsfc_g_kwh', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('engines', 'bsfc_g_kwh')
    op.drop_column('vehicles', 'fuel_tank_capacity_l')


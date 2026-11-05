"""add_pit_strategy_defaults_to_vehicle

Revision ID: f3a21b8c4e90
Revises: ee1328093dd5
Create Date: 2026-11-05 16:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a21b8c4e90'
down_revision: Union[str, None] = 'ee1328093dd5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('vehicles', sa.Column('pit_fuel_fill_rate_l_s',    sa.Float(), nullable=True))
    op.add_column('vehicles', sa.Column('pit_tire_change_time_s',     sa.Float(), nullable=True))
    op.add_column('vehicles', sa.Column('pit_brake_service_time_s',   sa.Float(), nullable=True))
    op.add_column('vehicles', sa.Column('pit_lane_delta_s',           sa.Float(), nullable=True))
    op.add_column('vehicles', sa.Column('pit_min_fuel_reserve_l',     sa.Float(), nullable=True))
    op.add_column('vehicles', sa.Column('pit_tire_wear_threshold',    sa.Float(), nullable=True))
    op.add_column('vehicles', sa.Column('pit_brake_wear_threshold',   sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('vehicles', 'pit_brake_wear_threshold')
    op.drop_column('vehicles', 'pit_tire_wear_threshold')
    op.drop_column('vehicles', 'pit_min_fuel_reserve_l')
    op.drop_column('vehicles', 'pit_lane_delta_s')
    op.drop_column('vehicles', 'pit_brake_service_time_s')
    op.drop_column('vehicles', 'pit_tire_change_time_s')
    op.drop_column('vehicles', 'pit_fuel_fill_rate_l_s')


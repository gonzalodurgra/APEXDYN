"""create_endurance_simulation_runs_table

Revision ID: ee1328093dd5
Revises: a619fc3bc1f0
Create Date: 2026-11-03 14:25:57.163855

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = 'ee1328093dd5'
down_revision: Union[str, Sequence[str], None] = 'a619fc3bc1f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'endurance_simulation_runs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('vehicle_id', sa.Uuid(), nullable=False),
        sa.Column('variant_id', sa.Uuid(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('reason_dnf', sa.String(length=255), nullable=True),
        sa.Column('total_laps_completed', sa.Integer(), nullable=False),
        sa.Column('total_distance_km', sa.Float(), nullable=False),
        sa.Column('total_race_time_s', sa.Float(), nullable=False),
        sa.Column('best_lap_time_s', sa.Float(), nullable=False),
        sa.Column('average_lap_time_s', sa.Float(), nullable=False),
        sa.Column('fuel_consumed_total_l', sa.Float(), nullable=False),
        sa.Column('total_pit_stops', sa.Integer(), nullable=False),
        sa.Column('total_time_in_pits_s', sa.Float(), nullable=False),
        sa.Column('finish_probability', sa.Float(), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=False),
        sa.Column('summary_metrics', sa.JSON(), nullable=False),
        sa.Column('components_status', sa.JSON(), nullable=False),
        sa.Column('pit_stops', sa.JSON(), nullable=False),
        sa.Column('failures', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['variant_id'], ['track_variants.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_endurance_sim_track_vehicle', 'endurance_simulation_runs', ['variant_id', 'vehicle_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_endurance_sim_track_vehicle', table_name='endurance_simulation_runs')
    op.drop_table('endurance_simulation_runs')

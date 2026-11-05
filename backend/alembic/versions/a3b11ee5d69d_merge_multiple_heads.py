"""merge multiple heads

Revision ID: a3b11ee5d69d
Revises: b749d1134a91, f3a21b8c4e90
Create Date: 2026-11-05 16:40:33.619635

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = 'a3b11ee5d69d'
down_revision: Union[str, Sequence[str], None] = ('b749d1134a91', 'f3a21b8c4e90')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

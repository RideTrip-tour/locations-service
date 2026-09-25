"""added border polygon to regions

Revision ID: 29850ecf6d5e
Revises: 6e56c7cbd0b6
Create Date: 2026-09-23 19:59:34.487134

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


revision: str = '29850ecf6d5e'
down_revision: Union[str, Sequence[str], None] = '6e56c7cbd0b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'regions',
        sa.Column(
            'border',
            geoalchemy2.types.Geography(
                geometry_type='MULTIPOLYGON',
                srid=4326,
                dimension=2,
                from_text='ST_GeogFromText',
                name='geography',
            ),
            nullable=True,
        ),
    )
    op.alter_column('regions', 'border', nullable=False)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_regions_border "
        "ON regions USING gist (border)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_regions_border")
    op.drop_column('regions', 'border')

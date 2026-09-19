"""coords to cities and locations

Revision ID: 6e56c7cbd0b6
Revises: 1b25bd9d2fc1
Create Date: 2026-09-18 16:29:46.019098

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = '6e56c7cbd0b6'
down_revision: Union[str, Sequence[str], None] = '1b25bd9d2fc1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.add_column(
        'cities',
        sa.Column(
            'coords',
            geoalchemy2.types.Geography(
                geometry_type='POINT', srid=4326,
                dimension=2, from_text='ST_GeogFromText', name='geography',
            ),
            nullable=True,
        ),
    )
    op.add_column(
        'locations',
        sa.Column(
            'coords',
            geoalchemy2.types.Geography(
                geometry_type='POINT', srid=4326,
                dimension=2, from_text='ST_GeogFromText', name='geography',
            ),
            nullable=True,
        ),
    )
    op.execute("""
        UPDATE locations
        SET coords = ST_GeogFromText('POINT(' || longitude || ' ' || latitude || ')')
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    """)
    op.alter_column('cities', 'coords', nullable=False)
    op.alter_column('locations', 'coords', nullable=False)
    op.alter_column(
        'locations', 'distance_to_city_km',
        existing_type=sa.INTEGER(),
        type_=sa.Numeric(precision=10, scale=3),
        existing_nullable=True,
        postgresql_using='distance_to_city_km::numeric(10,3)',
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_cities_coords "
        "ON cities USING gist (coords)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_locations_coords "
        "ON locations USING gist (coords)"
    )
    op.drop_column('locations', 'latitude')
    op.drop_column('locations', 'longitude')


def downgrade() -> None:
    op.add_column('locations', sa.Column('longitude', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    op.add_column('locations', sa.Column('latitude', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    op.execute("""
        UPDATE locations
        SET latitude = ST_Y(coords::geometry),
            longitude = ST_X(coords::geometry)
        WHERE coords IS NOT NULL
    """)

    op.alter_column(
        'locations', 'distance_to_city_km',
        existing_type=sa.Numeric(precision=10, scale=3),
        type_=sa.INTEGER(),
        existing_nullable=True,
        postgresql_using='distance_to_city_km::integer',
    )
    op.execute("DROP INDEX IF EXISTS idx_locations_coords")
    op.drop_column('locations', 'coords')
    op.execute("DROP INDEX IF EXISTS idx_cities_coords")
    op.drop_column('cities', 'coords')
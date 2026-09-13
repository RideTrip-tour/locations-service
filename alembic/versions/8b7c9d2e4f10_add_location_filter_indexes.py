"""Add indexes for location filters.

Revision ID: 8b7c9d2e4f10
Revises: f198bd16198d
Create Date: 2026-06-07 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8b7c9d2e4f10"
down_revision: str | Sequence[str] | None = "f198bd16198d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add btree expression and GIN indexes used by multi-value location filters."""
    op.create_index(
        "ix_locations_region_lower",
        "locations",
        [sa.text("lower(region)")],
        unique=False,
    )
    op.create_index(
        "ix_locations_city_lower", "locations", [sa.text("lower(city)")], unique=False
    )
    op.create_index(
        "ix_locations_country_lower",
        "locations",
        [sa.text("lower(country)")],
        unique=False,
    )
    op.create_index(
        "ix_locations_activity_ids_gin",
        "locations",
        ["activity_ids"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_locations_styles_gin",
        "locations",
        ["styles"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_locations_levels_gin",
        "locations",
        ["levels"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Remove indexes added for multi-value location filters."""
    op.drop_index(
        "ix_locations_levels_gin", table_name="locations", postgresql_using="gin"
    )
    op.drop_index(
        "ix_locations_styles_gin", table_name="locations", postgresql_using="gin"
    )
    op.drop_index(
        "ix_locations_activity_ids_gin", table_name="locations", postgresql_using="gin"
    )
    op.drop_index("ix_locations_country_lower", table_name="locations")
    op.drop_index("ix_locations_city_lower", table_name="locations")
    op.drop_index("ix_locations_region_lower", table_name="locations")

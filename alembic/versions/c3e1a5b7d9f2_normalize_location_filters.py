"""Normalize location activities, styles, and levels.

Revision ID: c3e1a5b7d9f2
Revises: 8b7c9d2e4f10
Create Date: 2026-08-25 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3e1a5b7d9f2"
down_revision: str | Sequence[str] | None = "8b7c9d2e4f10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Move location filter arrays into ordered many-to-many relationships."""
    op.create_table(
        "activities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "styles",
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("name"),
    )
    op.create_table(
        "levels",
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("name"),
    )
    op.create_table(
        "location_activities",
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("location_id", "activity_id"),
        sa.UniqueConstraint(
            "location_id", "position", name="uq_location_activities_position"
        ),
    )
    op.create_index(
        "ix_location_activities_activity_id",
        "location_activities",
        ["activity_id"],
        unique=False,
    )
    op.create_table(
        "location_styles",
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("style_name", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["style_name"], ["styles.name"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("location_id", "style_name"),
        sa.UniqueConstraint(
            "location_id", "position", name="uq_location_styles_position"
        ),
    )
    op.create_index(
        "ix_location_styles_style_name",
        "location_styles",
        ["style_name"],
        unique=False,
    )
    op.create_table(
        "location_levels",
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("level_name", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["level_name"], ["levels.name"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("location_id", "level_name"),
        sa.UniqueConstraint(
            "location_id", "position", name="uq_location_levels_position"
        ),
    )
    op.create_index(
        "ix_location_levels_level_name",
        "location_levels",
        ["level_name"],
        unique=False,
    )

    op.execute(
        """
        INSERT INTO activities (id)
        SELECT DISTINCT item.activity_id
        FROM locations AS location
        CROSS JOIN LATERAL unnest(location.activity_ids) AS item(activity_id)
        WHERE item.activity_id IS NOT NULL
        """
    )
    op.execute(
        """
        INSERT INTO styles (name)
        SELECT DISTINCT item.style_name
        FROM locations AS location
        CROSS JOIN LATERAL unnest(location.styles) AS item(style_name)
        WHERE item.style_name IS NOT NULL
        """
    )
    op.execute(
        """
        INSERT INTO levels (name)
        SELECT DISTINCT item.level_name
        FROM locations AS location
        CROSS JOIN LATERAL unnest(location.levels) AS item(level_name)
        WHERE item.level_name IS NOT NULL
        """
    )
    op.execute(
        """
        INSERT INTO location_activities (location_id, activity_id, position)
        SELECT location.id, item.activity_id, (min(item.position) - 1)::integer
        FROM locations AS location
        CROSS JOIN LATERAL unnest(location.activity_ids) WITH ORDINALITY
            AS item(activity_id, position)
        WHERE item.activity_id IS NOT NULL
        GROUP BY location.id, item.activity_id
        """
    )
    op.execute(
        """
        INSERT INTO location_styles (location_id, style_name, position)
        SELECT location.id, item.style_name, (min(item.position) - 1)::integer
        FROM locations AS location
        CROSS JOIN LATERAL unnest(location.styles) WITH ORDINALITY
            AS item(style_name, position)
        WHERE item.style_name IS NOT NULL
        GROUP BY location.id, item.style_name
        """
    )
    op.execute(
        """
        INSERT INTO location_levels (location_id, level_name, position)
        SELECT location.id, item.level_name, (min(item.position) - 1)::integer
        FROM locations AS location
        CROSS JOIN LATERAL unnest(location.levels) WITH ORDINALITY
            AS item(level_name, position)
        WHERE item.level_name IS NOT NULL
        GROUP BY location.id, item.level_name
        """
    )

    op.drop_index(
        "ix_locations_activity_ids_gin",
        table_name="locations",
        postgresql_using="gin",
    )
    op.drop_index(
        "ix_locations_styles_gin",
        table_name="locations",
        postgresql_using="gin",
    )
    op.drop_index(
        "ix_locations_levels_gin",
        table_name="locations",
        postgresql_using="gin",
    )
    op.drop_column("locations", "activity_ids")
    op.drop_column("locations", "styles")
    op.drop_column("locations", "levels")


def downgrade() -> None:
    """Restore arrays from the ordered many-to-many relationships."""
    op.add_column(
        "locations",
        sa.Column(
            "activity_ids",
            postgresql.ARRAY(sa.Integer()),
            server_default=sa.text("'{}'::integer[]"),
            nullable=False,
        ),
    )
    op.add_column(
        "locations",
        sa.Column(
            "styles",
            postgresql.ARRAY(sa.String()),
            server_default=sa.text("'{}'::varchar[]"),
            nullable=False,
        ),
    )
    op.add_column(
        "locations",
        sa.Column(
            "levels",
            postgresql.ARRAY(sa.String()),
            server_default=sa.text("'{}'::varchar[]"),
            nullable=False,
        ),
    )

    op.execute(
        """
        UPDATE locations AS location
        SET activity_ids = ARRAY(
                SELECT relation.activity_id
                FROM location_activities AS relation
                WHERE relation.location_id = location.id
                ORDER BY relation.position
            ),
            styles = ARRAY(
                SELECT relation.style_name
                FROM location_styles AS relation
                WHERE relation.location_id = location.id
                ORDER BY relation.position
            ),
            levels = ARRAY(
                SELECT relation.level_name
                FROM location_levels AS relation
                WHERE relation.location_id = location.id
                ORDER BY relation.position
            )
        """
    )

    op.drop_index("ix_location_levels_level_name", table_name="location_levels")
    op.drop_table("location_levels")
    op.drop_index("ix_location_styles_style_name", table_name="location_styles")
    op.drop_table("location_styles")
    op.drop_index(
        "ix_location_activities_activity_id", table_name="location_activities"
    )
    op.drop_table("location_activities")
    op.drop_table("levels")
    op.drop_table("styles")
    op.drop_table("activities")

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

"""expand location domain

Revision ID: 8f3c1a2b9d4e
Revises: 54fdb53e3676
Create Date: 2026-04-19 00:00:00.000000

"""

from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f3c1a2b9d4e"
down_revision: Union[str, Sequence[str], None] = "54fdb53e3676"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


location_kind = sa.Enum("resort", "city", "hotel", "landmark", name="location_kind")


def upgrade() -> None:
    location_kind.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "regions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "cities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("region_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["region_id"], ["regions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("region_id", "name", name="uq_city_region_name"),
    )
    op.create_index("ix_cities_region_id", "cities", ["region_id"])

    op.create_table(
        "activities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "levels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("name"),
    )

    op.add_column("location", sa.Column("display_name", sa.String(length=255), nullable=True))
    op.add_column("location", sa.Column("location_type", location_kind, nullable=False, server_default="resort"))
    op.add_column("location", sa.Column("region_id", sa.Integer(), nullable=True))
    op.add_column("location", sa.Column("city_id", sa.Integer(), nullable=True))
    op.alter_column("location", "user_id", existing_type=sa.Integer(), nullable=True)
    op.create_foreign_key(None, "location", "regions", ["region_id"], ["id"])
    op.create_foreign_key(None, "location", "cities", ["city_id"], ["id"])
    op.create_index("ix_location_region_id", "location", ["region_id"])
    op.create_index("ix_location_city_id", "location", ["city_id"])

    op.create_table(
        "location_activities",
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["location.id"]),
        sa.PrimaryKeyConstraint("location_id", "activity_id"),
    )

    op.create_table(
        "location_levels",
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("level_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["level_id"], ["levels.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["location.id"]),
        sa.PrimaryKeyConstraint("location_id", "level_id"),
    )

    op.create_table(
        "favorite_locations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["location_id"], ["location.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "location_id", name="uq_favorite_user_location"),
    )
    op.create_index("ix_favorite_locations_user_id", "favorite_locations", ["user_id"])
    op.create_index("ix_favorite_locations_location_id", "favorite_locations", ["location_id"])

    op.create_table(
        "trip_config_locations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("config_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["location_id"], ["location.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("config_id", "user_id", name="uq_trip_config_per_user"),
    )
    op.create_index("ix_trip_config_locations_config_id", "trip_config_locations", ["config_id"])
    op.create_index("ix_trip_config_locations_user_id", "trip_config_locations", ["user_id"])
    op.create_index("ix_trip_config_locations_location_id", "trip_config_locations", ["location_id"])

    op.create_index(
        "ix_location_coordinates_gist",
        "location",
        ["coordinates"],
        unique=False,
        postgresql_using="gist",
        postgresql_ops={"coordinates": "gist_geography_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_location_coordinates_gist", table_name="location")
    op.drop_index("ix_trip_config_locations_location_id", table_name="trip_config_locations")
    op.drop_index("ix_trip_config_locations_user_id", table_name="trip_config_locations")
    op.drop_index("ix_trip_config_locations_config_id", table_name="trip_config_locations")
    op.drop_table("trip_config_locations")

    op.drop_index("ix_favorite_locations_location_id", table_name="favorite_locations")
    op.drop_index("ix_favorite_locations_user_id", table_name="favorite_locations")
    op.drop_table("favorite_locations")

    op.drop_table("location_levels")
    op.drop_table("location_activities")

    op.drop_index("ix_location_city_id", table_name="location")
    op.drop_index("ix_location_region_id", table_name="location")
    op.drop_constraint(None, "location", type_="foreignkey")
    op.drop_constraint(None, "location", type_="foreignkey")
    op.alter_column("location", "user_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column("location", "city_id")
    op.drop_column("location", "region_id")
    op.drop_column("location", "location_type")
    op.drop_column("location", "display_name")

    op.drop_table("levels")
    op.drop_table("activities")
    op.drop_index("ix_cities_region_id", table_name="cities")
    op.drop_table("cities")
    op.drop_table("regions")

    location_kind.drop(op.get_bind(), checkfirst=True)

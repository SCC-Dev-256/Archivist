"""
# PURPOSE: Alembic migration to add cablecast_channel_id to helo_devices
# DEPENDENCIES: Alembic, SQLAlchemy
# MODIFICATION NOTES: v1 - add nullable integer column + index
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250808_add_helo_channel_id"
down_revision = "20250808_add_helo_tables"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("helo_devices", sa.Column("cablecast_channel_id", sa.Integer(), nullable=True))
    op.create_index("ix_helo_devices_channel_id", "helo_devices", ["cablecast_channel_id"])


def downgrade():
    op.drop_index("ix_helo_devices_channel_id", table_name="helo_devices")
    op.drop_column("helo_devices", "cablecast_channel_id")



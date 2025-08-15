"""
# PURPOSE: Alembic migration to add HELO device and schedule tables
# DEPENDENCIES: Alembic, SQLAlchemy
# MODIFICATION NOTES: v1 - create helo_devices, helo_schedules
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250808_add_helo_tables"
down_revision = "add_error_column"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'helo_devices',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('city_key', sa.String(length=50), nullable=False, index=True),
        sa.Column('ip', sa.String(length=100), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=True),
        sa.Column('password', sa.String(length=200), nullable=True),
        sa.Column('rtmp_url', sa.String(length=300), nullable=True),
        sa.Column('stream_key', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_unique_constraint('uq_helo_city_key', 'helo_devices', ['city_key'])

    op.create_table(
        'helo_schedules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('device_id', sa.Integer(), sa.ForeignKey('helo_devices.id'), nullable=False),
        sa.Column('cablecast_show_id', sa.Integer(), sa.ForeignKey('cablecast_shows.id'), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
    )



def downgrade():
    op.drop_table('helo_schedules')
    op.drop_constraint('uq_helo_city_key', 'helo_devices', type_='unique')
    op.drop_table('helo_devices')



"""Add Cablecast VOD integration tables

Revision ID: add_cablecast_vod_tables
Revises: 
Create Date: 2025-07-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_cablecast_vod_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create Cablecast VOD integration tables"""
    
    # Create cablecast_shows table
    op.create_table('cablecast_shows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cablecast_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('transcription_id', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['transcription_id'], ['transcription_results.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cablecast_id')
    )
    
    # Create cablecast_vods table
    op.create_table('cablecast_vods',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('show_id', sa.Integer(), nullable=False),
        sa.Column('quality', sa.Integer(), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('length', sa.Integer(), nullable=True),
        sa.Column('url', sa.String(length=500), nullable=True),
        sa.Column('embed_code', sa.Text(), nullable=True),
        sa.Column('web_vtt_url', sa.String(length=500), nullable=True),
        sa.Column('vod_state', sa.String(length=50), nullable=False),
        sa.Column('percent_complete', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['show_id'], ['cablecast_shows.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create cablecast_vod_chapters table
    op.create_table('cablecast_vod_chapters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vod_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('start_time', sa.Float(), nullable=False),
        sa.Column('end_time', sa.Float(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['vod_id'], ['cablecast_vods.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better performance
    op.create_index(op.f('ix_cablecast_shows_cablecast_id'), 'cablecast_shows', ['cablecast_id'], unique=True)
    op.create_index(op.f('ix_cablecast_shows_transcription_id'), 'cablecast_shows', ['transcription_id'], unique=False)
    op.create_index(op.f('ix_cablecast_vods_show_id'), 'cablecast_vods', ['show_id'], unique=False)
    op.create_index(op.f('ix_cablecast_vods_vod_state'), 'cablecast_vods', ['vod_state'], unique=False)
    op.create_index(op.f('ix_cablecast_vod_chapters_vod_id'), 'cablecast_vod_chapters', ['vod_id'], unique=False)


def downgrade():
    """Remove Cablecast VOD integration tables"""
    
    # Drop indexes
    op.drop_index(op.f('ix_cablecast_vod_chapters_vod_id'), table_name='cablecast_vod_chapters')
    op.drop_index(op.f('ix_cablecast_vods_vod_state'), table_name='cablecast_vods')
    op.drop_index(op.f('ix_cablecast_vods_show_id'), table_name='cablecast_vods')
    op.drop_index(op.f('ix_cablecast_shows_transcription_id'), table_name='cablecast_shows')
    op.drop_index(op.f('ix_cablecast_shows_cablecast_id'), table_name='cablecast_shows')
    
    # Drop tables
    op.drop_table('cablecast_vod_chapters')
    op.drop_table('cablecast_vods')
    op.drop_table('cablecast_shows') 
"""Add error column to transcription_results

Revision ID: add_error_column
Revises: f28a9d8074bb
Create Date: 2024-06-10 18:52:23.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_error_column'
down_revision = 'f28a9d8074bb'
branch_labels = None
depends_on = None

def upgrade():
    # Add error column to transcription_results table
    op.add_column('transcription_results', sa.Column('error', sa.Text(), nullable=True))

def downgrade():
    # Remove error column from transcription_results table
    op.drop_column('transcription_results', 'error') 
"""add_otp_challenges_table

Revision ID: 0002_add_otp_challenges
Revises: 0001_initial_canonical_schema
Create Date: 2026-10-22 19:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import models


# revision identifiers, used by Alembic.
revision: str = '0002_add_otp_challenges'
down_revision: Union[str, None] = '0001_initial_canonical_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'otp_challenges',
        sa.Column('id', models.GUID(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('purpose', sa.String(), nullable=False),
        sa.Column('code_hash', sa.String(), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('consumed', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('consumed_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('resend_available_at', sa.DateTime(), nullable=False),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_otp_challenges_email', 'otp_challenges', ['email'], unique=False)
    op.create_index('ix_otp_challenges_purpose', 'otp_challenges', ['purpose'], unique=False)
    op.create_index('ix_otp_challenges_code_hash', 'otp_challenges', ['code_hash'], unique=False)
    op.create_index('ix_otp_challenges_consumed', 'otp_challenges', ['consumed'], unique=False)
    op.create_index('ix_otp_challenges_expires_at', 'otp_challenges', ['expires_at'], unique=False)
    op.create_index('ix_otp_challenges_created_at', 'otp_challenges', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_otp_challenges_created_at', table_name='otp_challenges')
    op.drop_index('ix_otp_challenges_expires_at', table_name='otp_challenges')
    op.drop_index('ix_otp_challenges_consumed', table_name='otp_challenges')
    op.drop_index('ix_otp_challenges_code_hash', table_name='otp_challenges')
    op.drop_index('ix_otp_challenges_purpose', table_name='otp_challenges')
    op.drop_index('ix_otp_challenges_email', table_name='otp_challenges')
    op.drop_table('otp_challenges')

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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    required_columns = {
        'id', 'email', 'purpose', 'code_hash', 'attempts', 'max_attempts',
        'consumed', 'consumed_at', 'expires_at', 'resend_available_at',
        'ip_address', 'metadata_json', 'created_at'
    }

    expected_not_null = {
        'id', 'email', 'purpose', 'code_hash', 'attempts', 'max_attempts',
        'consumed', 'expires_at', 'resend_available_at'
    }

    if 'otp_challenges' not in tables:
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
    else:
        # Pre-existing table validation: fail safely if existing table has incompatible structure
        existing_cols = {c['name']: c for c in inspector.get_columns('otp_challenges')}
        missing_cols = required_columns - set(existing_cols.keys())
        if missing_cols:
            raise RuntimeError(
                f"[Migration 0002 Validation Error] Pre-existing 'otp_challenges' table is missing required columns: {sorted(missing_cols)}. "
                "Automatic adoption aborted to prevent schema corruption."
            )
        pk_info = inspector.get_pk_constraint('otp_challenges')
        if not pk_info or 'id' not in pk_info.get('constrained_columns', []):
            raise RuntimeError(
                "[Migration 0002 Validation Error] Pre-existing 'otp_challenges' table does not have 'id' as primary key. "
                "Automatic adoption aborted to prevent schema corruption."
            )
        # Validate nullability constraints
        for col_name in expected_not_null:
            col_info = existing_cols.get(col_name)
            if col_info and col_info.get('nullable') is True:
                raise RuntimeError(
                    f"[Migration 0002 Validation Error] Column '{col_name}' in pre-existing 'otp_challenges' must be NOT NULL. "
                    "Incompatible schema definition detected."
                )

    # Ensure all required indexes exist with exact definitions
    existing_indexes = {ix['name']: ix for ix in inspector.get_indexes('otp_challenges')} if 'otp_challenges' in inspector.get_table_names() else {}
    for col in ['email', 'purpose', 'code_hash', 'consumed', 'expires_at', 'created_at']:
        ix_name = f'ix_otp_challenges_{col}'
        if ix_name in existing_indexes:
            existing_ix = existing_indexes[ix_name]
            col_names = existing_ix.get('column_names', [])
            is_unique = existing_ix.get('unique', False)
            if col_names != [col] or is_unique:
                raise RuntimeError(
                    f"[Migration 0002 Validation Error] Pre-existing index '{ix_name}' has incompatible definition: "
                    f"columns={col_names} (expected [{col}]), unique={is_unique} (expected False)."
                )
        else:
            try:
                op.create_index(ix_name, 'otp_challenges', [col], unique=False)
            except Exception:
                pass


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'otp_challenges' in inspector.get_table_names():
        existing_indexes = {ix['name'] for ix in inspector.get_indexes('otp_challenges')}
        for col in ['email', 'purpose', 'code_hash', 'consumed', 'expires_at', 'created_at']:
            ix_name = f'ix_otp_challenges_{col}'
            if ix_name in existing_indexes:
                try:
                    op.drop_index(ix_name, table_name='otp_challenges')
                except Exception:
                    pass
        op.drop_table('otp_challenges')

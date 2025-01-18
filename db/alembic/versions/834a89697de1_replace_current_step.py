"""replace current_step

Revision ID: 834a89697de1
Revises: 3afc0d57deea
Create Date: 2025-01-06 12:22:59.460972

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '834a89697de1'
down_revision: Union[str, None] = '3afc0d57deea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user_words', 'current_step')
    op.add_column('users', sa.Column('current_step', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'current_step')
    op.add_column('user_words', sa.Column('current_step', sa.INTEGER(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###

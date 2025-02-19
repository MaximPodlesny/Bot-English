"""chenge on int

Revision ID: c9f89976cdc4
Revises: e7984c4ba5d0
Create Date: 2025-01-02 13:36:43.296871

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9f89976cdc4'
down_revision: Union[str, None] = 'e7984c4ba5d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('telegram_id', sa.Integer(), nullable=True))
    op.create_unique_constraint(None, 'users', ['telegram_id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'users', type_='unique')
    op.drop_column('users', 'telegram_id')
    # ### end Alembic commands ###

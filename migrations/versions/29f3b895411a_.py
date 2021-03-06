"""empty message

Revision ID: 29f3b895411a
Revises: de0fba40d62d
Create Date: 2017-11-16 18:39:49.996801

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '29f3b895411a'
down_revision = 'de0fba40d62d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('setting',
    sa.Column('name', sa.String(255), nullable=True),
    sa.Column('value', sa.Text(), nullable=True)
    )
    op.add_column(u'task_log', sa.Column('need_check', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column(u'task_log', 'need_check')
    op.drop_table('setting')
    # ### end Alembic commands ###

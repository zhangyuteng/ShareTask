"""empty message

Revision ID: 36214d43d386
Revises: fe8f80675ee4
Create Date: 2017-10-22 22:16:30.066253

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '36214d43d386'
down_revision = 'fe8f80675ee4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('paraphrase', sa.Column('ch', sa.Text(), nullable=True))
    op.add_column('paraphrase', sa.Column('en', sa.Text(), nullable=True))
    op.add_column('sample', sa.Column('ch', sa.Text(), nullable=True))
    op.add_column('sample', sa.Column('en', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('sample', 'en')
    op.drop_column('sample', 'ch')
    op.drop_column('paraphrase', 'en')
    op.drop_column('paraphrase', 'ch')
    # ### end Alembic commands ###

"""empty message

Revision ID: 75f2f6f99897
Revises: c05d2dbca672
Create Date: 2017-10-28 13:25:14.581003

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '75f2f6f99897'
down_revision = 'c05d2dbca672'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('dictionary', sa.Column('chose_dictionary', sa.String(length=60), nullable=True))
    op.drop_column('task', 'chose_dictionary')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('task', sa.Column('chose_dictionary', mysql.VARCHAR(collation=u'utf8mb4_unicode_ci', length=60), nullable=True))
    op.drop_column('dictionary', 'chose_dictionary')
    # ### end Alembic commands ###

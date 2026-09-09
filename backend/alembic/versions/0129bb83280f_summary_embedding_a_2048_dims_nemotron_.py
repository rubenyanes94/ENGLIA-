"""summary_embedding a 2048 dims (nemotron-3-embed-1b)

Revision ID: 0129bb83280f
Revises: a4cfe70d518e
Create Date: 2026-09-09 13:15:51.208313

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy  # autogenerate lo referencia pero no lo importa (ver migración inicial)


# revision identifiers, used by Alembic.
revision: str = '0129bb83280f'
down_revision: Union[str, None] = 'a4cfe70d518e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Los vectores existentes se BORRAN antes de ampliar la columna, y no
    # es una limpieza opcional: un vector de 768 dimensiones producido por
    # nomic-embed-text no se puede convertir en uno de 2048 de
    # nemotron-3-embed-1b. No es que "falten números" — son espacios
    # vectoriales distintos, así que rellenar con ceros daría distancias
    # sin sentido y una memoria de largo plazo que recuerda mal, que es
    # peor que no recordar.
    #
    # Se regeneran solos: Celery vuelve a resumir y embeber cada sesión al
    # cerrarla (ver app/workers/). Hoy además esta columna está vacía en
    # todas las filas, así que en este entorno no se pierde nada.
    op.execute("UPDATE conversation_sessions SET summary_embedding = NULL")

    op.alter_column('conversation_sessions', 'summary_embedding',
               existing_type=pgvector.sqlalchemy.vector.VECTOR(dim=768),
               type_=pgvector.sqlalchemy.vector.VECTOR(dim=2048),
               existing_nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # Mismo motivo que en upgrade, en sentido contrario.
    op.execute("UPDATE conversation_sessions SET summary_embedding = NULL")

    op.alter_column('conversation_sessions', 'summary_embedding',
               existing_type=pgvector.sqlalchemy.vector.VECTOR(dim=2048),
               type_=pgvector.sqlalchemy.vector.VECTOR(dim=768),
               existing_nullable=True)
    # ### end Alembic commands ###

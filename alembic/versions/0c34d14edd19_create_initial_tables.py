"""create initial tables

Revision ID: 0c34d14edd19
Revises:
Create Date: 2025-02-09 15:10:34.548946
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0c34d14edd19"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create documents table
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Create document_pages table
    op.create_table(
        "document_pages",
        sa.Column("id", sa.String(length=255), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id"),
            nullable=False,
        ),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
    )

    # Create document_page_embeddings table
    op.create_table(
        "document_page_embeddings",
        sa.Column(
            "document_page_id",
            sa.String(length=255),
            sa.ForeignKey("document_pages.id"),
            primary_key=True,
        ),
        sa.Column("embedding", Vector(1536), nullable=False),
    )

    # Add HNSW index for vector search
    op.create_index(
        "embedding_hnsw_index",
        "document_page_embeddings",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    # Create document_tags table
    op.create_table(
        "document_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True, index=True),
    )

    # Create document_page_tags table (association table)
    op.create_table(
        "document_page_tags",
        sa.Column(
            "document_page_id",
            sa.String(length=255),
            sa.ForeignKey("document_pages.id"),
            primary_key=True,
        ),
        sa.Column(
            "document_tag_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_tags.id"),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    # Drop tables in reverse order to handle dependencies
    op.drop_table("document_page_tags")
    op.drop_index("embedding_hnsw_index", table_name="document_page_embeddings")
    op.drop_table("document_page_embeddings")
    op.drop_table("document_pages")
    op.drop_table("document_tags")
    op.drop_table("documents")

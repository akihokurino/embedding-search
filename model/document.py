from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    UUID,
    Integer,
    Text,
    String,
    ForeignKey,
    Index,
    Table,
    Column,
    DateTime,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from model.base import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    pages = relationship("DocumentPage", back_populates="document")


class DocumentPage(Base):
    __tablename__ = "document_pages"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    document = relationship("Document", back_populates="pages")
    tags = relationship(
        "DocumentTag",
        secondary="document_page_tags",
        back_populates="document_pages",
    )
    embedding = relationship(
        "DocumentPageEmbeddings", back_populates="document_page", uselist=False
    )


class DocumentPageEmbeddings(Base):
    __tablename__ = "document_page_embeddings"

    document_page_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("document_pages.id"), primary_key=True
    )
    embedding: Mapped[Vector] = mapped_column(Vector(1536), nullable=False)

    document_page = relationship("DocumentPage", back_populates="embedding")



class DocumentTag(Base):
    __tablename__ = "document_tags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )

    document_pages = relationship(
        "DocumentPage", secondary="document_page_tags", back_populates="tags"
    )


document_page_tags = Table(
    "document_page_tags",
    Base.metadata,
    Column(
        "document_page_id",
        String(255),
        ForeignKey("document_pages.id"),
        primary_key=True,
    ),
    Column(
        "document_tag_id",
        UUID(as_uuid=True),
        ForeignKey("document_tags.id"),
        primary_key=True,
    ),
)

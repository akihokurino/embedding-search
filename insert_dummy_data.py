# mypy: ignore-errors
from datetime import datetime
from random import randint, sample
from uuid import uuid4

import numpy as np
from factory import LazyAttribute, Faker, SubFactory
from factory.alchemy import SQLAlchemyModelFactory
from numpy.typing import NDArray
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from const import DATABASE_URL
from model.document import (
    Document,
    DocumentPage,
    DocumentPageEmbeddings,
    DocumentTag,
    document_page_tags,
)

engine = create_engine(DATABASE_URL, echo=False)
session = scoped_session(sessionmaker(bind=engine))


def random_normalized_vector() -> NDArray[np.float64]:
    vector = np.random.rand(1536)
    norm = np.linalg.norm(vector)
    normalized_vector = vector / norm
    return normalized_vector


class DocumentFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Document
        sqlalchemy_session = session
        sqlalchemy_session_persistence = "commit"

    id = LazyAttribute(lambda _: uuid4())
    name = Faker("sentence")
    file_path = LazyAttribute(lambda _: f"input/{uuid4()}.pdf")
    created_at = LazyAttribute(lambda _: datetime.now())


class DocumentPageFactory(SQLAlchemyModelFactory):
    class Meta:
        model = DocumentPage
        sqlalchemy_session = session
        sqlalchemy_session_persistence = "commit"

    document = SubFactory(DocumentFactory)

    id = LazyAttribute(lambda _: str(uuid4()))
    document_id = LazyAttribute(lambda obj: obj.document.id)
    number = LazyAttribute(lambda _: randint(1, 50))
    text = Faker("text")
    summary = Faker("text")


class DocumentPageEmbeddingsFactory(SQLAlchemyModelFactory):
    class Meta:
        model = DocumentPageEmbeddings
        sqlalchemy_session = session
        sqlalchemy_session_persistence = "commit"

    document_page = SubFactory(DocumentPageFactory)

    document_page_id = LazyAttribute(lambda obj: obj.document_page.id)
    embedding = LazyAttribute(lambda _: random_normalized_vector())


class DocumentTagFactory(SQLAlchemyModelFactory):
    class Meta:
        model = DocumentTag
        sqlalchemy_session = session
        sqlalchemy_session_persistence = "commit"

    id = LazyAttribute(lambda _: uuid4())
    name = Faker("word")


if __name__ == "__main__":
    tags = [DocumentTagFactory.create() for _ in range(10)]

    for _ in range(5):
        document = DocumentFactory.create()

        for page_num in range(1, 11):
            page = DocumentPageFactory.create(document=document, number=page_num)
            embeddings = DocumentPageEmbeddingsFactory.create(document_page=page)

            page_tags = sample(tags, k=randint(1, 3))
            for tag in page_tags:
                session.execute(
                    document_page_tags.insert().values(
                        document_page_id=page.id,
                        document_tag_id=tag.id,
                    )
                )
                session.commit()

    session.close()

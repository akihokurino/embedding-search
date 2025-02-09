from __future__ import annotations

import os
from datetime import datetime
from typing import final

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from model.document import DocumentPage, DocumentPageEmbeddings
from openai import OpenAI
from pydantic import BaseModel
from pypdf import PdfReader
from sqlalchemy import create_engine, select
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import sessionmaker

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = f"postgresql+psycopg2://postgres:postgres@localhost:5432/sample"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
openAIClient = OpenAI(
    api_key=OPENAI_API_KEY,
)
app = FastAPI(
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


def embedding_search(query_embedding: list[float]) -> list[_DocumentPageResp]:
    with SessionLocal() as session:
        cosine_distance = DocumentPageEmbeddings.embedding.cosine_distance(
            query_embedding
        ).label("distance")

        query = (
            select(DocumentPage, cosine_distance)
            .join(
                DocumentPageEmbeddings,
                DocumentPage.id == DocumentPageEmbeddings.document_page_id,
            )
            .options(joinedload(DocumentPage.tags), joinedload(DocumentPage.document))
            .order_by(cosine_distance)
            .limit(3)
        )

        results = session.execute(query).unique().all()

        response: list[_DocumentPageResp] = []
        for page, distance in results:
            document_resp = _DocumentResp(
                id=str(page.document.id),
                name=page.document.name,
                created_at=page.document.created_at,
            )

            page_resp = _DocumentPageResp(
                id=page.id,
                document_id=str(page.document_id),
                page_number=page.number,
                text=page.text,
                summary=page.summary,
                tags=[tag.name for tag in page.tags],
                document=document_resp,
            )
            response.append(page_resp)

        return response


@final
class _SearchByTextPayload(BaseModel):
    text: str


@final
class _SearchByFilePayload(BaseModel):
    path: str


@final
class _DocumentResp(BaseModel):
    id: str
    name: str
    created_at: datetime


@final
class _DocumentPageResp(BaseModel):
    id: str
    document_id: str
    page_number: int
    text: str
    summary: str
    tags: list[str]

    document: _DocumentResp


@app.get("/search_by_text")
async def _search_by_text(
    payload: _SearchByTextPayload,
) -> list[_DocumentPageResp]:
    embedding_response = openAIClient.embeddings.create(
        model="text-embedding-ada-002", input=[payload.text[:4000]]
    )
    query_embedding = embedding_response.data[0].embedding
    return embedding_search(query_embedding)


@app.get("/search_by_file")
async def _search_by_file(
    payload: _SearchByFilePayload,
) -> list[_DocumentPageResp]:
    file_path = os.path.join(os.path.dirname(__file__), "input", payload.path)
    reader = PdfReader(str(file_path))
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""

    embedding_response = openAIClient.embeddings.create(
        model="text-embedding-ada-002", input=[text[:4000]]
    )
    query_embedding = embedding_response.data[0].embedding
    return embedding_search(query_embedding)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="debug")

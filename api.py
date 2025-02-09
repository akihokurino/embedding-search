from __future__ import annotations

import os
from datetime import datetime
from typing import final

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from model.document import Document, DocumentPage
from openai import OpenAI
from pydantic import BaseModel
from sqlalchemy import create_engine
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


@final
class _SearchPayload(BaseModel):
    q: str


@final
class _DocumentResp(BaseModel):
    id: str
    name: str
    pages: list[_DocumentPageResp]
    created_at: datetime


@final
class _DocumentPageResp(BaseModel):
    id: str
    document_id: str
    page_number: int
    text: str
    summary: str
    tags: list[str]


@app.get("/documents")
async def _documents(
    request: Request,
) -> list[_DocumentResp]:
    session = SessionLocal()
    response: list[_DocumentResp] = []

    try:
        documents = (
            session.query(Document)
            .options(joinedload(Document.pages).joinedload(DocumentPage.tags))
            .all()
        )

        for doc in documents:
            pages: list[DocumentPage] = doc.pages
            document_pages_resp = [
                _DocumentPageResp(
                    id=page.id,
                    document_id=str(page.document_id),
                    page_number=page.number,
                    text=page.text,
                    summary=page.summary,
                    tags=[tag.name for tag in page.tags],
                )
                for page in pages
            ]

            document_resp = _DocumentResp(
                id=str(doc.id),
                name=str(doc.name),
                pages=document_pages_resp,
                created_at=doc.created_at,
            )
            response.append(document_resp)
    finally:
        session.close()

    return response


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="debug")

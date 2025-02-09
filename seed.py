import json
import os
import pickle
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from model.document import (
    Document,
    DocumentPage,
    DocumentPageEmbeddings,
    DocumentTag,
    document_page_tags,
)

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/sample"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

client = OpenAI(
    api_key=OPENAI_API_KEY,
)

SYSTEM_PROMPT = """
あなたはプロフェッショナルの編集者です。
与えられた文書情報を簡潔かつ明確に要約することが得意です。
"""

USER_PROMPT_TEMPLATE = """
以下の文章は PDF から抽出した1ページ分のテキストです。
この内容を簡潔に要約し、関連するタグも抽出してください。
JSON形式で出力してください。

# 出力フォーマット
- 要約: xxx
- タグ: [xxx, xxx, xxx]

# テキスト
{text}
"""


def create_file_table_df() -> pd.DataFrame:
    columns = ["file_id", "file_name", "file_path"]
    return pd.DataFrame(columns=columns)


def create_page_table_df() -> pd.DataFrame:
    columns = ["page_id", "file_id", "page_number", "text"]
    return pd.DataFrame(columns=columns)


def create_dataframes() -> tuple[pd.DataFrame, pd.DataFrame]:
    file_cache_path = cache_dir / "file_table.pkl"
    page_cache_path = cache_dir / "page_table.pkl"

    if file_cache_path.exists() and page_cache_path.exists():
        with open(file_cache_path, "rb") as f:
            cached_file_df: pd.DataFrame = pickle.load(f)
        with open(page_cache_path, "rb") as f:
            cached_page_df: pd.DataFrame = pickle.load(f)
        print("✅ キャッシュから file_table_df と page_table_df を読み込みました。")
        return cached_file_df, cached_page_df
    else:
        new_file_table_df = create_file_table_df()
        new_page_table_df = create_page_table_df()

        pdf_files = list(input_dir.glob("*.pdf"))
        for pdf_file in pdf_files:
            file_id = str(uuid.uuid4())
            new_file_table_df = append_to_file_table(
                new_file_table_df, file_id, pdf_file
            )
            texts = extract_text_from_pdf(pdf_file)
            for i, text in enumerate(texts):
                new_page_table_df = append_to_page_table(
                    new_page_table_df, i, file_id, text
                )

        with open(file_cache_path, "wb") as f:
            pickle.dump(new_file_table_df, f)
            print(f"✅ データをキャッシュに保存しました: {file_cache_path.name}")
        with open(page_cache_path, "wb") as f:
            pickle.dump(new_page_table_df, f)
            print(f"✅ データをキャッシュに保存しました: {page_cache_path.name}")

        return new_file_table_df, new_page_table_df


def extract_text_from_pdf(_file_path: Path) -> list[str]:
    reader = PdfReader(str(_file_path))
    return [page.extract_text() or "" for page in reader.pages]


def append_to_file_table(
        df: pd.DataFrame, _file_id: str, _file_path: Path
) -> pd.DataFrame:
    new_data = {
        "file_id": [_file_id],
        "file_name": [_file_path.name],
        "file_path": [str(_file_path)],
    }
    return pd.concat([df, pd.DataFrame(new_data)], ignore_index=True)


def append_to_page_table(
        df: pd.DataFrame, _index: int, _file_id: str, _text: str
) -> pd.DataFrame:
    new_data = {
        "page_id": [_file_id + "_" + str(_index)],
        "file_id": [_file_id],
        "page_number": [_index + 1],
        "text": [_text],
    }
    return pd.concat([df, pd.DataFrame(new_data)], ignore_index=True)


def get_embedding(_text: str) -> list[float]:
    response = client.embeddings.create(
        model="text-embedding-ada-002", input=[_text[:4000]]
    )
    return response.data[0].embedding


def append_to_page_table_embeddings(df: pd.DataFrame, _cache_dir: Path) -> pd.DataFrame:
    cache_path = _cache_dir / "page_table_with_embeddings.pkl"
    if cache_path.exists():
        with open(cache_path, "rb") as f:
            cached_df: pd.DataFrame = pickle.load(f)
        print("✅ キャッシュからEmbeddingデータを読み込みました。")
        return cached_df

    print("⏳ Embeddingを取得中...")
    embeddings: list[list[float]] = []
    for index, (_, row) in enumerate(df.iterrows()):
        input_text = str(row["text"])

        if not input_text.strip():
            embeddings.append([])
            continue

        embedding = get_embedding(input_text)
        embeddings.append(embedding)
        print(f"Processing {index + 1}/{len(df)}")

    df["embedding"] = embeddings

    with open(cache_path, "wb") as f:
        pickle.dump(df, f)
    print("✅ Embedding結果をキャッシュに保存しました。")

    return df


def get_llm_features(_text: str) -> dict[str, Any]:
    user_prompt = USER_PROMPT_TEMPLATE.format(text=_text[:4000])

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    if content is None:
        return {"要約": "", "出典": "", "タグ": []}
    try:
        result: dict[str, Any] = json.loads(content)
        return result
    except json.JSONDecodeError:
        return {"要約": "", "出典": "", "タグ": []}


def append_to_page_table_llm_features(
        df: pd.DataFrame, _cache_dir: Path
) -> pd.DataFrame:
    cache_path = _cache_dir / "page_table_with_llm.pkl"

    if cache_path.exists():
        with open(cache_path, "rb") as f:
            cached_df: pd.DataFrame = pickle.load(f)
        print("✅ キャッシュから要約データを読み込みました。")
        return cached_df

    print("⏳ Summaryを取得中...")
    summaries: list[str] = []
    tags: list[list[str]] = []
    for index, (_, row) in enumerate(df.iterrows()):
        input_text = str(row["text"])

        if not input_text.strip():
            summaries.append("")
            tags.append([])
            continue

        llm_result = get_llm_features(input_text)
        summaries.append(llm_result.get("要約", ""))
        tags.append(llm_result.get("タグ", []))
        print(f"Processing {index + 1}/{len(df)}")

    df["summary"] = summaries
    df["tags"] = tags

    with open(cache_path, "wb") as f:
        pickle.dump(df, f)
    print("✅ 要約結果をキャッシュに保存しました。")

    return df


def insert_data_to_db(file_df: pd.DataFrame, page_df: pd.DataFrame) -> None:
    def remove_null_bytes(v: str) -> str:
        return v.replace("\x00", "")

    session = SessionLocal()
    try:
        for _, file_row in file_df.iterrows():
            document = Document(
                id=uuid.UUID(str(file_row["file_id"])),
                name=str(file_row["file_name"]),
                file_path=str(file_row["file_path"]),
                created_at=datetime.now(),
            )
            session.add(document)
            session.flush()

        for _, page_row in page_df.iterrows():
            document_page = DocumentPage(
                id=str(page_row["page_id"]),
                document_id=uuid.UUID(str(page_row["file_id"])),
                number=int(page_row["page_number"]),
                text=remove_null_bytes(str(page_row["text"])),
                summary=remove_null_bytes(page_row.get("summary", "")),
            )
            session.add(document_page)
            session.flush()

            if page_row.get("embedding"):
                embedding = DocumentPageEmbeddings(
                    document_page_id=str(page_row["page_id"]),
                    embedding=page_row["embedding"],
                )
                session.add(embedding)
                session.flush()

            for tag_name in page_row.get("tags", []):
                if remove_null_bytes(tag_name) == "":
                    continue

                tag = session.query(DocumentTag).filter_by(name=tag_name).first()
                if not tag:
                    tag_id = str(uuid.uuid4())
                    tag = DocumentTag(
                        id=uuid.UUID(tag_id), name=remove_null_bytes(tag_name)
                    )
                    session.add(tag)
                    session.flush()

                session.execute(
                    document_page_tags.insert().values(
                        document_page_id=str(page_row["page_id"]),
                        document_tag_id=tag.id,
                    )
                )

        session.commit()
        print("✅ データベースへのインサートが完了しました。")
    except Exception as e:
        session.rollback()
        print(f"❌ エラー発生: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    input_dir = Path("./input")
    output_dir = Path("./output")
    cache_dir = Path("./cache")
    now = datetime.now()

    assert input_dir.exists(), f"{input_dir} does not exist"
    output_dir.mkdir(exist_ok=True)
    cache_dir.mkdir(exist_ok=True)

    file_table_df, page_table_df = create_dataframes()
    page_table_df = append_to_page_table_embeddings(page_table_df, cache_dir)
    page_table_df = append_to_page_table_llm_features(page_table_df, cache_dir)

    file_table_df.to_csv(output_dir / "file_table.csv", index=False)
    page_table_df.to_csv(output_dir / "page_table.csv", index=False)

    insert_data_to_db(file_table_df, page_table_df)

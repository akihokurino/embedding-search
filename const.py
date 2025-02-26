import os

from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
DB_HOST = os.getenv("DB_HOST", "localhost")
DATABASE_URL = (
    f"postgresql+psycopg2://postgres:postgres@{DB_HOST}:5432/embedding_search"
)
EMBEDDING_MODEL = "text-embedding-3-small"

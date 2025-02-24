import os

from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/embedding_search"
EMBEDDING_MODEL = "text-embedding-3-small"

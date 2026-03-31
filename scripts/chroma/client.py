import chromadb
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import PROJECT_ROOT

CHROMA_DB_PATH = str(PROJECT_ROOT / "data" / "chroma_db")


def get_client():
    return chromadb.PersistentClient(path=CHROMA_DB_PATH)


def get_collection():
    return get_client().get_or_create_collection(
        name="exam_questions",
        metadata={"hnsw:space": "cosine"},
    )

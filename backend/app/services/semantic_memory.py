from __future__ import annotations

import hashlib
import logging
import os
import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

import chromadb
from chromadb.config import Settings as ChromaSettings

logger = logging.getLogger("officepilot.semantic_memory")

COLLECTION_NAME = "invoice_embeddings"

MOCK_EMBEDDING_DIMENSION = 128


class MockEmbeddingFunction:
    """Deterministic mock embedding that hashes text to a fixed-length vector.

    This avoids needing ML models or external embedding services during tests.
    In production, swap to ChromaDB's default all-MiniLM-L6-v2 or Ollama embeddings.
    """

    def __call__(self, input: list[str]) -> list[list[float]]:
        return self._embed(input)

    def embed_query(self, input: str | list[str]) -> list[list[float]]:
        texts = input if isinstance(input, list) else [input]
        return self._embed(texts)

    def embed_document(self, input: str | list[str]) -> list[list[float]]:
        texts = input if isinstance(input, list) else [input]
        return self._embed(texts)

    @staticmethod
    def _embed(input: list[str]) -> list[list[float]]:
        results = []
        for text in input:
            h = hashlib.sha256(text.encode("utf-8")).hexdigest()
            vec = [int(h[i : i + 2], 16) / 255.0 for i in range(0, min(256, len(h)), 2)]
            while len(vec) < MOCK_EMBEDDING_DIMENSION:
                vec.append(0.0)
            results.append(vec[:MOCK_EMBEDDING_DIMENSION])
        return results


class SemanticMemory:
    """Local vector database for semantic search across invoice data.

    Uses ChromaDB in persistent mode, backed by a mock embedding function
    by default (deterministic, no deps). Pass embedding_function=None to use
    ChromaDB's built-in default embedding (all-MiniLM-L6-v2 via onnxruntime).
    """

    def __init__(
        self,
        persist_dir: str | Path | None = None,
        embedding_function: Any = None,
    ):
        self._persist_dir: Path | None = None
        self._client: chromadb.ClientAPI | None = None
        self._collection: chromadb.Collection | None = None
        self._embedding_function = embedding_function or MockEmbeddingFunction()

        if persist_dir is not None:
            self.initialize(persist_dir)

    def initialize(self, persist_dir: str | Path) -> None:
        self._persist_dir = Path(persist_dir)
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(self._persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        existing = [c.name for c in self._client.list_collections()]
        if COLLECTION_NAME in existing:
            self._collection = self._client.get_collection(
                name=COLLECTION_NAME,
                embedding_function=self._embedding_function,
            )
        else:
            self._collection = self._client.create_collection(
                name=COLLECTION_NAME,
                embedding_function=self._embedding_function,
            )
        logger.info("SemanticMemory initialized at %s", self._persist_dir)

    @property
    def collection(self) -> chromadb.Collection:
        if self._collection is None:
            raise RuntimeError(
                "SemanticMemory not initialized. Call initialize(persist_dir) first."
            )
        return self._collection

    def index_invoice(
        self,
        invoice_id: str,
        text_content: str,
        metadata: dict | None = None,
    ) -> str:
        meta = dict(metadata or {})
        meta.pop("text_content", None)
        doc_id = str(uuid4())
        self.collection.add(
            documents=[text_content],
            metadatas=[meta],
            ids=[doc_id],
        )
        logger.debug(
            "Indexed invoice %s (doc_id=%s): %s", invoice_id, doc_id, meta
        )
        return doc_id

    def semantic_search(
        self,
        query: str,
        top_k: int = 5,
        user_id: int | None = None,
    ) -> list[dict]:
        where_filter = None
        if user_id is not None:
            where_filter = {"user_id": user_id}

        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_filter,
        )

        out: list[dict] = []
        ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        documents = results.get("documents", [[]])[0]

        for i in range(len(ids)):
            out.append({
                "id": ids[i],
                "score": 1.0 - (distances[i] if i < len(distances) else 0.0),
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "text_content": documents[i][:500] if i < len(documents) else "",
            })
        return out

    def count(self) -> int:
        return self.collection.count()

    def reset(self) -> None:
        if self._client is not None:
            self._client.delete_collection(COLLECTION_NAME)
        self._collection = None

    def clear_persist_dir(self) -> None:
        if self._persist_dir is not None and self._persist_dir.exists():
            shutil.rmtree(self._persist_dir)
            self._persist_dir.mkdir(parents=True, exist_ok=True)


_instance: SemanticMemory | None = None


def get_semantic_memory() -> SemanticMemory:
    global _instance
    if _instance is None:
        from ..config import get_settings

        settings = get_settings()
        persist_dir = os.environ.get(
            "OFFICEPILOT_VECTOR_STORE_DIR",
            str(settings.data_dir / "vector_store"),
        )
        _instance = SemanticMemory(persist_dir=persist_dir)
    return _instance


def reset_semantic_memory() -> None:
    global _instance
    if _instance is not None:
        try:
            _instance.reset()
        except Exception:
            pass
        _instance = None

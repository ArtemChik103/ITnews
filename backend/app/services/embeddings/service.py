import asyncio
from dataclasses import dataclass

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings

_model: SentenceTransformer | None = None


@dataclass(slots=True)
class EmbeddingResult:
    embedding: list[float] | None
    embedding_model: str | None
    status: str
    error: str | None = None


class EmbeddingService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def generate(self, article_id: int, title: str, content_clean: str, language: str) -> EmbeddingResult:
        del article_id, language
        input_text = build_embedding_input(title=title, content_clean=content_clean)
        if not input_text:
            return EmbeddingResult(
                embedding=None,
                embedding_model=self.settings.embedding_model,
                status="skipped",
                error="empty title and content",
            )

        try:
            embedding = await asyncio.to_thread(self._encode, input_text)
        except Exception as exc:  # noqa: BLE001
            return EmbeddingResult(
                embedding=None,
                embedding_model=self.settings.embedding_model,
                status="failed",
                error=str(exc),
            )

        return EmbeddingResult(
            embedding=embedding,
            embedding_model=self.settings.embedding_model,
            status="ready",
        )

    def _encode(self, text: str) -> list[float]:
        model = get_sentence_transformer()
        embedding = model.encode(text, normalize_embeddings=True)
        vector = np.asarray(embedding, dtype=np.float32)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector.tolist()


def build_embedding_input(title: str, content_clean: str) -> str:
    settings = get_settings()
    title_clean = (title or "").strip()
    content = (content_clean or "").strip()
    if title_clean and content:
        return f"{title_clean}\n\n{content[: settings.embedding_max_chars]}"
    if title_clean:
        return title_clean
    if content:
        return content[: settings.embedding_max_chars]
    return ""


def get_sentence_transformer() -> SentenceTransformer:
    global _model
    if _model is None:
        settings = get_settings()
        _model = SentenceTransformer(settings.embedding_model)
    return _model

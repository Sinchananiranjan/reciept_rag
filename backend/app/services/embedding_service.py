import json
import hashlib
from typing import List
from app.config import settings

class EmbeddingService:
    def get_embedding(self, text: str) -> List[float]:
        """Generates 384-dimensional vector embedding using OpenAI or local deterministic fallback."""
        if settings.OPENAI_API_KEY and len(settings.OPENAI_API_KEY.strip()) > 5:
            try:
                return self._get_openai_embedding(text)
            except Exception as e:
                print(f"OpenAI embedding error ({str(e)}), using local embedding generator.")

        return self._get_local_embedding(text)

    def _get_openai_embedding(self, text: str) -> List[float]:
        import urllib.request
        req_data = json.dumps({
            "model": settings.EMBEDDING_MODEL,
            "input": text
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.openai.com/v1/embeddings",
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
            }
        )

        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["data"][0]["embedding"]

    def _get_local_embedding(self, text: str) -> List[float]:
        """Fast, deterministic local vector embedding (384 dimensions) for local development."""
        dim = 384
        vec = [0.0] * dim
        words = text.lower().split()
        if not words:
            return vec

        for word in words:
            # Hash word into vector components
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            idx = h % dim
            val = ((h >> 8) % 1000) / 500.0 - 1.0  # value between -1.0 and 1.0
            vec[idx] += val

        # Normalize vector to unit length
        norm = sum(x * x for x in vec) ** 0.5
        if norm > 1e-6:
            vec = [x / norm for x in vec]

        return vec

embedding_service = EmbeddingService()

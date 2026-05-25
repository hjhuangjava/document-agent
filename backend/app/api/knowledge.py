"""Knowledge-base search API – mock results for now."""

import time
from fastapi import APIRouter
from pydantic import BaseModel

from app.engine.tools import _simple_search, MOCK_DOCS

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class KnowledgeSearchRequest(BaseModel):
    query: str
    top_k: int = 5


class KnowledgeSearchResult(BaseModel):
    id: str
    title: str
    content: str
    score: float
    source: str
    category: str
    updated_at: str


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: list[KnowledgeSearchResult]
    total: int


@router.post("/search", response_model=KnowledgeSearchResponse)
def search_knowledge(body: KnowledgeSearchRequest):
    """Search the knowledge base with a free-text query.

    Currently uses a simple keyword-match mock. Will be replaced by
    real vector / embedding-based search in the future.
    """
    time.sleep(0.3)  # simulate network / retrieval latency

    results = _simple_search(body.query, MOCK_DOCS, body.top_k)

    return KnowledgeSearchResponse(
        query=body.query,
        results=[KnowledgeSearchResult(**r) for r in results],
        total=len(results),
    )

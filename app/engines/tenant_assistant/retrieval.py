"""Knowledge retrieval for the tenant assistant.

Scores published support_knowledge_articles against a question and returns the
best passages with a normalised 0..1 score. The score is what gates the LLM:
below the configured threshold the assistant refuses instead of guessing.

Why trigram + keyword rather than embeddings, today: the help centre is a
small corpus of short articles, and `pg_trgm` is already installed. Lexical
scoring on a corpus this size beats a 384-dim cosine search and costs nothing
per query. `search()` returns the same shape either way, so swapping in
pgvector later is a change inside this module only.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "to", "of", "and", "or",
    "in", "on", "for", "with", "how", "do", "does", "did", "i", "my", "me", "we",
    "our", "you", "your", "can", "could", "should", "would", "what", "why",
    "when", "where", "which", "who", "it", "its", "this", "that", "there",
    "please", "help", "need", "want", "get", "not", "no", "any", "am",
}


@dataclass
class Passage:
    article_id: str
    slug: str
    title: str
    summary: str | None
    body: str | None
    product_area: str
    score: float

    def as_citation(self) -> dict:
        return {"article_id": self.article_id, "slug": self.slug,
                "title": self.title, "product_area": self.product_area,
                "score": round(self.score, 4)}

    def as_context(self) -> str:
        parts = [f"[{self.slug}] {self.title}"]
        if self.summary:
            parts.append(self.summary.strip())
        if self.body:
            parts.append(self.body.strip())
        return "\n".join(parts)


@dataclass
class Retrieval:
    passages: list[Passage] = field(default_factory=list)

    @property
    def top_score(self) -> float:
        return self.passages[0].score if self.passages else 0.0

    @property
    def is_empty(self) -> bool:
        return not self.passages

    def citations(self) -> list[dict]:
        return [p.as_citation() for p in self.passages]

    def context_block(self) -> str:
        return "\n\n---\n\n".join(p.as_context() for p in self.passages)


def tokenize(question: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", (question or "").lower())
    return [w for w in words if len(w) > 2 and w not in _STOPWORDS]


async def search(
    db: AsyncSession,
    question: str,
    *,
    top_k: int = 5,
    product_areas: list[str] | None = None,
) -> Retrieval:
    """Rank published articles for `question`.

    Score blends three signals, all computed in Postgres:
      * trigram similarity on title (strongest — titles are task-shaped)
      * trigram similarity on summary
      * how many of the question's content words appear in body/keywords
    """
    tokens = tokenize(question)
    if not tokens:
        return Retrieval()

    cleaned = " ".join(tokens)
    # Each token contributes to a lexical hit count over body + keywords.
    token_clause = " + ".join(
        f"(CASE WHEN lower(coalesce(a.body,'') || ' ' || coalesce(a.summary,'') || ' ' "
        f"|| a.title || ' ' || coalesce(a.keywords::text,'')) LIKE :tok{i} THEN 1 ELSE 0 END)"
        for i in range(len(tokens))
    )
    params: dict = {"q": cleaned, "top_k": top_k}
    for i, tok in enumerate(tokens):
        params[f"tok{i}"] = f"%{tok}%"

    area_sql = ""
    if product_areas:
        area_sql = " AND a.product_area = ANY(:areas)"
        params["areas"] = product_areas

    sql = text(f"""
        SELECT a.id, a.slug, a.title, a.summary, a.body, a.product_area,
               similarity(lower(a.title), :q)                    AS title_sim,
               similarity(lower(coalesce(a.summary, '')), :q)    AS summary_sim,
               ({token_clause})::float / {len(tokens)}           AS token_hit
        FROM support_knowledge_articles a
        WHERE a.is_published = true{area_sql}
        ORDER BY (
            similarity(lower(a.title), :q) * 0.55
          + similarity(lower(coalesce(a.summary, '')), :q) * 0.15
          + (({token_clause})::float / {len(tokens)}) * 0.30
        ) DESC
        LIMIT :top_k
    """)

    rows = (await db.execute(sql, params)).mappings().all()

    passages: list[Passage] = []
    for r in rows:
        score = (float(r["title_sim"] or 0) * 0.55
                 + float(r["summary_sim"] or 0) * 0.15
                 + float(r["token_hit"] or 0) * 0.30)
        if score <= 0:
            continue
        passages.append(Passage(
            article_id=str(r["id"]), slug=r["slug"], title=r["title"],
            summary=r["summary"], body=r["body"],
            product_area=r["product_area"], score=score,
        ))
    return Retrieval(passages=passages)


async def by_area(db: AsyncSession, product_area: str, limit: int = 12) -> list[Passage]:
    """Every published article in one product area — backs a `topic` option."""
    rows = (await db.execute(text("""
        SELECT id, slug, title, summary, body, product_area
        FROM support_knowledge_articles
        WHERE is_published = true AND product_area = :area
        ORDER BY is_featured DESC, view_count DESC, title
        LIMIT :limit
    """), {"area": product_area, "limit": limit})).mappings().all()
    return [Passage(article_id=str(r["id"]), slug=r["slug"], title=r["title"],
                    summary=r["summary"], body=r["body"],
                    product_area=r["product_area"], score=1.0) for r in rows]


async def by_slug(db: AsyncSession, slug: str) -> Passage | None:
    r = (await db.execute(text("""
        SELECT id, slug, title, summary, body, product_area
        FROM support_knowledge_articles
        WHERE is_published = true AND slug = :slug
    """), {"slug": slug})).mappings().first()
    if not r:
        return None
    return Passage(article_id=str(r["id"]), slug=r["slug"], title=r["title"],
                   summary=r["summary"], body=r["body"],
                   product_area=r["product_area"], score=1.0)


async def most_asked(db: AsyncSession, limit: int = 5,
                     product_areas: list[str] | None = None) -> list[Passage]:
    """Articles tenants actually open, so the panel reflects real demand."""
    params: dict = {"limit": limit}
    area_sql = ""
    if product_areas:
        area_sql = " AND product_area = ANY(:areas)"
        params["areas"] = product_areas
    rows = (await db.execute(text(f"""
        SELECT id, slug, title, summary, body, product_area
        FROM support_knowledge_articles
        WHERE is_published = true{area_sql}
        ORDER BY (view_count * 2 + helpful_count * 3) DESC, is_featured DESC, title
        LIMIT :limit
    """), params)).mappings().all()
    return [Passage(article_id=str(r["id"]), slug=r["slug"], title=r["title"],
                    summary=r["summary"], body=r["body"],
                    product_area=r["product_area"], score=1.0) for r in rows]


async def areas_available(db: AsyncSession) -> list[dict]:
    rows = (await db.execute(text("""
        SELECT product_area, count(*) AS n
        FROM support_knowledge_articles
        WHERE is_published = true
        GROUP BY product_area
        ORDER BY product_area
    """))).mappings().all()
    return [{"product_area": r["product_area"], "article_count": int(r["n"])} for r in rows]


async def record_view(db: AsyncSession, article_id: str) -> None:
    await db.execute(text(
        "UPDATE support_knowledge_articles SET view_count = view_count + 1 WHERE id = :id"
    ), {"id": article_id})

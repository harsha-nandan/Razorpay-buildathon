"""Keyword-relevance catalog search, closer to how Amazon/Flipkart-style
search boxes behave than a single ILIKE substring match: the query is
tokenized and matched against title, description, category, and tags, with
plural/singular tolerance (e.g. "earbud" still matches "earbuds"), and
results are ranked by how many query terms actually hit, not just returned
in whatever order the database gives them.

Always tries to surface at least MIN_RESULTS products (backfilling with the
next-best relevance matches, ignoring the category/price filters, if the
strict match is thin) so a shopper always has real options to compare
instead of a single hit or an empty page.
"""

import re

from sqlalchemy.orm import Session

from ..models import Product

_TOKEN_RE = re.compile(r"[a-z0-9]+")
MIN_RESULTS = 5


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def _product_tokens(p: Product) -> set[str]:
    return _tokenize(" ".join([p.title, p.description, p.category, *p.tags]))


def _relevance_score(query_tokens: set[str], p: Product) -> int:
    if not query_tokens:
        return 0
    haystack = _product_tokens(p)
    exact_hits = query_tokens & haystack
    partial_hits = 0
    for qt in query_tokens - exact_hits:
        if any(qt in ht or ht in qt for ht in haystack if len(qt) > 2 and len(ht) > 2):
            partial_hits += 1
    return len(exact_hits) * 2 + partial_hits


def search_products(
    db: Session,
    query: str = "",
    category: str = "",
    max_price_paise: int = 0,
    limit: int = 10,
) -> list[Product]:
    q = db.query(Product).filter(Product.in_stock.is_(True))
    if category:
        q = q.filter(Product.category.ilike(category))
    if max_price_paise:
        q = q.filter(Product.price_paise <= max_price_paise)
    candidates = q.all()

    query_tokens = _tokenize(query)

    if not query_tokens:
        results = sorted(candidates, key=lambda p: (p.price_paise, -p.rating))
    else:
        scored = [(p, _relevance_score(query_tokens, p)) for p in candidates]
        scored = [(p, s) for p, s in scored if s > 0]
        # Same relevance and price is a real tie (e.g. three earbuds at the
        # same price point) - break it by rating so a shopper/agent sees the
        # better-reviewed option first instead of an arbitrary insertion order.
        scored.sort(key=lambda pair: (-pair[1], pair[0].price_paise, -pair[0].rating))
        results = [p for p, _ in scored]

    if len(results) < MIN_RESULTS:
        results = _backfill(db, query_tokens, already=results, target=min(MIN_RESULTS, limit))

    return results[:limit]


def _backfill(db: Session, query_tokens: set[str], already: list[Product], target: int) -> list[Product]:
    """Top up thin results with the next-best matches from the whole
    in-stock catalog, ignoring category/price filters - real e-commerce
    search never leaves a shopper with fewer than a handful of options."""
    have_skus = {p.sku for p in already}
    pool = [p for p in db.query(Product).filter(Product.in_stock.is_(True)).all() if p.sku not in have_skus]

    if query_tokens:
        pool.sort(key=lambda p: (-_relevance_score(query_tokens, p), p.price_paise, -p.rating))
    else:
        pool.sort(key=lambda p: (p.price_paise, -p.rating))

    results = list(already)
    for p in pool:
        if len(results) >= target:
            break
        results.append(p)
    return results

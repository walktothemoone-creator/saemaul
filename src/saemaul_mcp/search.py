"""검색과 발췌. / Matching and snippets.

한국어 자료라서 형태소 분석기 없이도 쓸 수 있게 만들었다.
비교할 때 공백과 문장부호를 지우므로 "새마을 운동"과 "새마을운동"이 같게 걸린다.
동의어 사전(data/search_aliases.yaml)으로 검색어를 넓힌 뒤 점수를 매긴다.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any

from .corpus import Corpus, Haystack, as_text, build_haystack, normalize, tokenize

WEAK_MATCH_MIN_LEN = 3  # 낱말 중간에서 걸린 말은 이 길이 이상일 때만 인정한다
WEAK_MATCH_WEIGHT = 0.35

SNIPPET_WINDOW = 140


def normalize_with_map(text: str) -> tuple[str, list[int]]:
    """정규화 문자열과, 그 각 글자가 원문 몇 번째 글자였는지의 대응표."""
    out: list[str] = []
    index: list[int] = []
    for position, char in enumerate(text):
        folded = unicodedata.normalize("NFKC", char).casefold()
        for piece in folded:
            if piece.isalnum():
                out.append(piece)
                index.append(position)
    return "".join(out), index


def snippet(text: str, needles: set[str], window: int = SNIPPET_WINDOW) -> str:
    """찾은 말 주변만 잘라 낸다. 못 찾으면 앞부분을 돌려준다."""
    flat, index = normalize_with_map(text)
    best = -1
    for needle in needles:
        if not needle:
            continue
        found = flat.find(needle)
        if found != -1 and (best == -1 or found < best):
            best = found
    if best == -1 or not index:
        return text if len(text) <= window else text[: window - 1].rstrip() + "…"
    center = index[min(best, len(index) - 1)]
    start = max(0, center - window // 2)
    end = min(len(text), center + window // 2)
    piece = text[start:end].strip()
    return ("…" if start > 0 else "") + piece + ("…" if end < len(text) else "")


@dataclass(slots=True)
class Hit:
    kind: str  # "passage" | "source"
    score: float
    matched: int
    payload: dict[str, Any]


@dataclass(slots=True)
class Query:
    """낱말별 동의어 묶음 + 붙여 쓴 전체 검색어."""

    groups: list[set[str]]
    phrase: str

    @property
    def needles(self) -> set[str]:
        found = {v for group in self.groups for v in group}
        if self.phrase:
            found.add(self.phrase)
        return found

    def __bool__(self) -> bool:
        return bool(self.groups or self.phrase)


def build_query(corpus: Corpus, text: str) -> Query:
    # "경쟁적 지원"처럼 띄어 쓴 복합어가 사전에 통째로 있으면 그쪽을 먼저 쓴다.
    whole = normalize(text)
    if whole and whole in corpus.aliases:
        return Query(groups=[set(corpus.aliases[whole])], phrase="")
    groups: list[set[str]] = []
    for token in tokenize(text):
        variants = {v for v in corpus.expand(token) if v}
        if variants:
            groups.append(variants)
    phrase = normalize(text) if len(groups) > 1 else ""
    return Query(groups=groups, phrase=phrase)


def _occurrences(haystack: Haystack, needle: str) -> tuple[int, int]:
    """낱말 첫머리에서 걸린 횟수와 낱말 중간에서 걸린 횟수."""
    if not needle or not haystack.text:
        return 0, 0
    strong = weak = 0
    start = haystack.text.find(needle)
    while start != -1:
        if start in haystack.starts:
            strong += 1
        else:
            weak += 1
        start = haystack.text.find(needle, start + 1)
    return strong, weak


def _variant_score(haystack: Haystack, variant: str) -> float:
    strong, weak = _occurrences(haystack, variant)
    if not strong and (not weak or len(variant) < WEAK_MATCH_MIN_LEN):
        return 0.0
    score = 1.0 + min(max(strong - 1, 0), 3) * 0.25 if strong else 0.0
    if weak and len(variant) >= WEAK_MATCH_MIN_LEN:
        score += WEAK_MATCH_WEIGHT if not strong else WEAK_MATCH_WEIGHT / 2
    return score


def _score(haystack: Haystack, query: Query) -> tuple[float, int]:
    """점수와, 몇 개의 낱말이 걸렸는지."""
    if not haystack or not query.groups:
        return 0.0, 0
    total = 0.0
    matched = 0
    for group in query.groups:
        best = max((_variant_score(haystack, variant) for variant in group), default=0.0)
        if best > 0:
            matched += 1
            total += best
    if query.phrase and _variant_score(haystack, query.phrase) > 0:
        total += 2.0  # 띄어쓰기만 다른 정확한 구절
    return total, matched


def search_passages(
    corpus: Corpus, query: str, document_id: str = "", limit: int = 10
) -> list[Hit]:
    parsed = build_query(corpus, query)
    if not parsed:
        return []
    needles = parsed.needles
    hits: list[Hit] = []
    for passage in corpus.all_passages():
        if document_id and passage.doc_id != document_id:
            continue
        score, matched = _score(passage.haystack, parsed)
        if not matched:
            continue
        if passage.kind == "heading":
            score += 0.5
        hits.append(
            Hit(
                kind="passage",
                score=score,
                matched=matched,
                payload=passage.summary(snippet(passage.text, needles)),
            )
        )
    hits.sort(key=lambda h: (-h.matched, -h.score, h.payload["passage_id"]))
    # 모든 낱말이 걸린 단락을 먼저 보여 주고, 없으면 일부라도 걸린 단락을 보여 준다.
    chosen = [h for h in hits if h.matched == len(parsed.groups)] or hits
    return chosen if limit <= 0 else chosen[:limit]


def search_sources(corpus: Corpus, query: str, limit: int = 10) -> list[Hit]:
    parsed = build_query(corpus, query)
    if not parsed:
        return []
    hits: list[Hit] = []
    for source in corpus.sources:
        source_id = str(source.get("id"))
        score, matched = _score(corpus.source_haystack(source_id), parsed)
        if not matched:
            continue
        hits.append(Hit(kind="source", score=score, matched=matched, payload=corpus.source_summary(source)))
    hits.sort(key=lambda h: (-h.matched, -h.score, h.payload["id"]))
    chosen = [h for h in hits if h.matched == len(parsed.groups)] or hits
    return chosen if limit <= 0 else chosen[:limit]


def search_documents(corpus: Corpus, query: str, limit: int = 5) -> list[Hit]:
    """문서 자체를 서지 정보로 찾는다. 예: 박정희, 1972, 친필"""
    parsed = build_query(corpus, query)
    if not parsed:
        return []
    hits: list[Hit] = []
    for doc in corpus.documents.values():
        score, matched = _score(corpus.document_haystack(doc.id), parsed)
        if not matched:
            continue
        hits.append(Hit(kind="document", score=score, matched=matched, payload=doc.card()))
    hits.sort(key=lambda h: (-h.matched, -h.score, h.payload["document_id"]))
    chosen = [h for h in hits if h.matched == len(parsed.groups)] or hits
    return chosen if limit <= 0 else chosen[:limit]


def topic_matches(source: dict[str, Any], topic: str) -> bool:
    """use_for 태그 맞춤. 띄어쓰기 차이와 부분 일치를 허용한다."""
    if not topic.strip():
        return True
    needle = normalize(topic)
    for tag in source.get("use_for") or []:
        flat = normalize(str(tag))
        if needle == flat or needle in flat or flat in needle:
            return True
    return False


def keyword_matches(corpus: Corpus, source: dict[str, Any], keyword: str) -> bool:
    if not keyword.strip():
        return True
    haystack = corpus.source_haystack(str(source.get("id"))) or build_haystack(as_text(source))
    variants = corpus.expand(keyword) | {normalize(keyword)}
    return any(_variant_score(haystack, variant) > 0 for variant in variants)

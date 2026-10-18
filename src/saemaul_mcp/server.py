"""새마을 MCP 서버. / Saemaul MCP server.

표준 MCP로 동작한다. 특정 회사의 에이전트에 묶여 있지 않다.
stdio는 로컬 프로세스를 띄우는 클라이언트용, streamable-http는 URL로 붙는 클라이언트용이다.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from .corpus import (
    LAYERS,
    RELATIONS,
    STANCES,
    VERIFY_STATUSES,
    Corpus,
    Document,
)
from .search import (
    keyword_matches,
    search_documents,
    search_passages,
    search_sources,
    topic_matches,
)

__all__ = ["build_server", "get_corpus"]

INSTRUCTIONS = """\
Saemaul Undong (South Korea, 1970s) research server: a curated source registry plus
full-text primary documents. Two rules: cite only ids returned by these tools, and never
invent a source, URL, archival number or quotation. Start with saemaul_overview. Use
saemaul_search for any question. When a topic is contested, call saemaul_compare_stances so
critical and supportive sources are both visible. Always report verify_status when it is
needs_check, and never cite titles listed by saemaul_editorial_notes as excluded.

새마을운동 자료 서버다. 서지 레지스트리와 전문을 가진 1차 기록을 함께 제공한다.
이 도구가 돌려준 id만 인용한다. 목록에 없는 자료, URL, 기록물 번호, 인용문을 지어내지 않는다.
처음에는 saemaul_overview를 부른다. 논쟁이 있는 주제는 saemaul_compare_stances로
비판 출처와 그 외 출처를 함께 본다. needs_check 상태는 사용자에게 그대로 알린다.
"""

_corpus: Corpus | None = None


def get_corpus() -> Corpus:
    global _corpus
    if _corpus is None:
        _corpus = Corpus()
    return _corpus


def _error(message: str, **extra: Any) -> dict[str, Any]:
    return {"error": message, **extra}


def _reject(field: str, value: str, allowed: tuple[str, ...]) -> dict[str, Any] | None:
    if value and value not in allowed:
        return _error(f"{field} 값이 목록에 없습니다: {value}", **{f"allowed_{field}": list(allowed)})
    return None


def _cross_reference(corpus: Corpus, doc: Document, passage_id: str) -> dict[str, Any] | None:
    entry = doc.cross_references.get(passage_id)
    if not entry:
        return None
    links = []
    for link in entry["links"]:
        source = corpus.source(str(link.get("source")))
        if not source:
            continue
        relation = str(link.get("relation") or "interprets")
        links.append(
            {
                "relation": relation if relation in RELATIONS else "interprets",
                **corpus.source_summary(source),
            }
        )
    return {"note": entry.get("note"), "related_sources": links} if links else None


def build_server(host: str = "127.0.0.1", port: int = 8765) -> FastMCP:
    corpus = get_corpus()
    mcp = FastMCP(
        "saemaul",
        instructions=INSTRUCTIONS,
        host=host,
        port=port,
        stateless_http=True,
        json_response=True,
        log_level="WARNING",
    )

    # ----------------------------------------------------------------- 둘러보기
    @mcp.tool()
    def saemaul_overview() -> dict[str, Any]:
        """이 서버에 무엇이 있고 어떻게 찾는지. 처음 한 번 부른다.
        What this server holds and how to search it. Call this first."""
        meta = corpus.registry.get("meta") or {}
        stats = corpus.stats()
        return {
            "scope": meta.get("scope"),
            "registry_version": meta.get("registry_version"),
            "editorial_policy": meta.get("editorial_policy") or [],
            "counts": stats,
            "documents": [doc.card() for doc in corpus.documents.values()],
            "vocabularies": {
                "stance": list(STANCES),
                "layer": list(LAYERS),
                "verify_status": list(VERIFY_STATUSES),
                "relation": list(RELATIONS),
            },
            "how_to": [
                "아무 질문이든 saemaul_search(query)로 시작한다. 원문 단락과 서지를 함께 돌려준다.",
                "단락을 인용하려면 saemaul_read_passage로 앞뒤 문맥과 관련 연구를 함께 받는다.",
                "논쟁 주제는 saemaul_compare_stances(topic)으로 관점별로 나눠 본다.",
                "Start with saemaul_search(query); it returns both primary passages and bibliography.",
                "Quote only via saemaul_read_passage, which returns the citation string to use.",
            ],
            "limits": [
                "이 저장소는 새마을운동 기록물 전부를 담고 있지 않다. 전문은 documents에 있는 것뿐이다.",
                "needs_check 표시는 아직 원문·URL 대조가 끝나지 않았다는 뜻이다.",
                "This is a curated index, not the full 22,084-item archive.",
            ],
        }

    @mcp.tool()
    def saemaul_search(query: str, scope: str = "all", limit: int = 8) -> dict[str, Any]:
        """자유로운 말로 자료를 찾는다. 원문 단락과 서지 출처를 함께 돌려준다.
        Search everything with plain language; returns primary passages and bibliography.

        query: 찾는 말. 한글·한자·영어 모두 된다. 띄어쓰기 차이는 무시한다.
        scope: all | documents(원문 단락만) | sources(서지만)
        limit: 각 묶음의 반환 상한. 0 이하면 전부.
        """
        if not query.strip():
            return _error("검색어가 비어 있습니다.", hint="예: 자발성, 경쟁적 지원, 새마을 정신, 부녀회")
        if scope not in ("all", "documents", "sources"):
            return _error(f"scope 값이 올바르지 않습니다: {scope}", allowed_scope=["all", "documents", "sources"])

        result: dict[str, Any] = {"query": query, "scope": scope}
        if scope in ("all", "documents"):
            hits = search_passages(corpus, query, limit=limit)
            result["passages"] = [h.payload for h in hits]
            result["passage_count"] = len(hits)
            matching_docs = [h.payload for h in search_documents(corpus, query, limit=3)]
            if matching_docs:
                result["documents"] = matching_docs
        if scope in ("all", "sources"):
            hits = search_sources(corpus, query, limit=limit)
            result["sources"] = [h.payload for h in hits]
            result["source_count"] = len(hits)
        if not result.get("passage_count") and not result.get("source_count") and not result.get("documents"):
            result["hint"] = "걸린 자료가 없습니다. saemaul_list_topics로 주제 태그를 확인하거나 더 짧은 말로 찾아보세요."
            result["topics"] = list(corpus.topics())[:30]
        return result

    # ------------------------------------------------------------------- 원문
    @mcp.tool()
    def saemaul_list_documents() -> dict[str, Any]:
        """전문을 보유한 문서 목록과 서지·권리 상태.
        Documents held here in full text, with provenance and rights status."""
        return {
            "count": len(corpus.documents),
            "documents": [doc.card() for doc in corpus.documents.values()],
        }

    @mcp.tool()
    def saemaul_get_document(document_id: str, section: str = "") -> dict[str, Any]:
        """문서의 목차를 보거나, 장 하나의 전문을 읽는다.
        Document outline, or the full text of one section.

        document_id: 예 DOC-1972-0426
        section: 장 번호. 비우면 목차와 서지만 돌려준다.
        """
        doc = corpus.document(document_id)
        if doc is None:
            return _error(
                f"'{document_id}' 문서가 없습니다.",
                available=list(corpus.documents),
                hint="saemaul_list_documents로 id를 확인합니다.",
            )
        outline = [
            {
                "section": s.get("number"),
                "heading": s.get("heading"),
                "passages": len(s.get("passages") or []),
            }
            for s in doc.sections
        ]
        payload: dict[str, Any] = {
            **doc.card(),
            "archival_reference": doc.meta.get("archival_reference"),
            "transcription": doc.meta.get("transcription"),
            "rights": doc.meta.get("rights"),
            "scan": doc.meta.get("scan"),
            "outline": outline,
        }
        if not section:
            payload["glossary"] = doc.glossary
            payload["hint"] = "section에 장 번호를 넣으면 그 장의 전문을 돌려줍니다."
            return payload

        wanted = str(section).strip().lstrip("§")
        chosen = next((s for s in doc.sections if str(s.get("number")) == wanted), None)
        if chosen is None:
            return _error(
                f"'{section}' 장이 없습니다.",
                available=[s.get("number") for s in doc.sections],
            )
        ids = set(chosen.get("passages") or [])
        payload["section"] = {
            "number": chosen.get("number"),
            "heading": chosen.get("heading"),
            "passages": [p.summary() for p in doc.passages if p.id in ids],
        }
        payload.pop("outline", None)
        return payload

    @mcp.tool()
    def saemaul_read_passage(document_id: str, passage_id: str, context: int = 1) -> dict[str, Any]:
        """단락 하나를 앞뒤 문맥, 인용 표기, 관련 연구와 함께 읽는다. 인용은 이 도구로 한다.
        Read one passage with context, a ready-to-use citation, and related scholarship.

        passage_id: p068 같은 id 또는 §10-(4) 같은 인용 표기.
        context: 앞뒤로 함께 보여 줄 단락 수.
        """
        doc = corpus.document(document_id)
        if doc is None:
            return _error(f"'{document_id}' 문서가 없습니다.", available=list(corpus.documents))
        passage = doc.passage(passage_id)
        if passage is None:
            return _error(
                f"'{passage_id}' 단락이 없습니다.",
                hint="saemaul_search 결과의 passage_id 또는 citation을 그대로 씁니다.",
            )
        order = [p.id for p in doc.passages]
        position = order.index(passage.id)
        span = max(0, context)
        before = [p.summary() for p in doc.passages[max(0, position - span) : position]]
        after = [p.summary() for p in doc.passages[position + 1 : position + 1 + span]]
        payload: dict[str, Any] = {
            "document_id": doc.id,
            "document_title": doc.meta.get("title"),
            "citation": passage.citation,
            "cite_as": (
                f"{doc.meta.get('author') or '미상'}, 「{doc.meta.get('title')}」"
                f"({doc.meta.get('date')}), {passage.ref}"
            ),
            "passage": passage.summary(),
            "before": before,
            "after": after,
            "transcription_status": (doc.meta.get("transcription") or {}).get("verify_status"),
            "scan": (doc.meta.get("scan") or {}).get("file"),
        }
        linked = _cross_reference(corpus, doc, passage.id)
        if linked:
            payload["cross_reference"] = linked
        return payload

    # ------------------------------------------------------------------- 서지
    @mcp.tool()
    def saemaul_find_sources(
        topic: str = "",
        stance: str = "",
        layer: str = "",
        keyword: str = "",
        verify_status: str = "",
        limit: int = 50,
    ) -> dict[str, Any]:
        """조건을 걸어 서지 출처를 추린다.
        Filter the bibliography by topic, stance, layer, keyword or verification state.

        topic: 주제 태그(use_for). 부분 일치 허용. 예 도농격차
        stance: supportive | critical | analytical | foundational
        layer: primary | scholarly | theory | ontology | infra
        keyword: 제목·저자·소장처·이론·핵심 주장에서 찾을 말
        verify_status: url_verified | needs_check
        """
        for field, value, allowed in (
            ("stance", stance, STANCES),
            ("layer", layer, LAYERS),
            ("verify_status", verify_status, VERIFY_STATUSES),
        ):
            rejected = _reject(field, value, allowed)
            if rejected:
                return rejected

        matched = [
            corpus.source_summary(source)
            for source in corpus.sources
            if topic_matches(source, topic)
            and (not stance or source.get("stance") == stance)
            and (not layer or source.get("layer") == layer)
            and (not verify_status or source.get("verify_status") == verify_status)
            and keyword_matches(corpus, source, keyword)
        ]
        shown = matched if limit <= 0 else matched[:limit]
        return {
            "count": len(matched),
            "returned": len(shown),
            "truncated": len(shown) < len(matched),
            "sources": shown,
        }

    @mcp.tool()
    def saemaul_get_source(source_id: str) -> dict[str, Any]:
        """출처 id 하나의 전체 레코드. 전문을 보유한 출처면 문서 id도 함께 돌려준다.
        The full record for one source id, plus its document id when the text is held here."""
        source = corpus.source(source_id)
        if source is None:
            return _error(
                f"'{source_id}' 출처가 레지스트리에 없습니다.",
                hint="saemaul_search 또는 saemaul_find_sources로 id를 확인합니다.",
            )
        payload = dict(source)
        doc_id = source.get("document_id")
        if doc_id and (doc := corpus.document(str(doc_id))):
            payload["document"] = doc.card()
        return payload

    @mcp.tool()
    def saemaul_compare_stances(topic: str) -> dict[str, Any]:
        """한 주제를 관점별로 갈라 보여 준다. 논쟁이 있는 주제는 이 도구를 쓴다.
        Split one topic by stance so criticism and support are visible side by side."""
        grouped: dict[str, list[dict[str, Any]]] = {stance: [] for stance in STANCES}
        for source in corpus.sources:
            if topic_matches(source, topic):
                stance = str(source.get("stance") or "")
                if stance in grouped:
                    grouped[stance].append(corpus.source_summary(source))
        passages = [h.payload for h in search_passages(corpus, topic, limit=5)]
        count = sum(len(v) for v in grouped.values())
        result: dict[str, Any] = {
            "topic": topic,
            "source_count": count,
            **grouped,
            "primary_passages": passages,
        }
        if not count and not passages:
            result["hint"] = "그런 주제 태그가 없습니다. topics 안에서 고릅니다."
            result["topics"] = list(corpus.topics())
        return result

    @mcp.tool()
    def saemaul_list_topics() -> dict[str, Any]:
        """주제 태그와 태그별 자료 수. 검색 전에 말을 고를 때 쓴다.
        Topic tags with counts; use them to pick search terms."""
        topics = corpus.topics()
        return {"count": len(topics), "topics": topics}

    @mcp.tool()
    def saemaul_editorial_notes() -> dict[str, Any]:
        """확인이 덜 끝난 자료, 근거에서 뺀 자료와 이유, 권리 상태.
        What is unverified, what was excluded and why, and the rights status of held scans."""
        unverified = [
            corpus.source_summary(s) for s in corpus.sources if s.get("verify_status") == "needs_check"
        ]
        rights = [
            {
                "document_id": doc.id,
                "title": doc.meta.get("title"),
                "rights": doc.meta.get("rights"),
                "archival_reference": doc.meta.get("archival_reference"),
                "transcription": doc.meta.get("transcription"),
            }
            for doc in corpus.documents.values()
        ]
        return {
            "unverified_count": len(unverified),
            "unverified": unverified,
            "excluded_count": len(corpus.excluded),
            "excluded": corpus.excluded,
            "excluded_note": "여기 적힌 제목은 이 저장소의 편집 결정으로 뺀 것이다. 근거로 인용하지 않는다.",
            "document_rights": rights,
        }

    # -------------------------------------------------------------- 리소스/프롬프트
    @mcp.resource("saemaul://overview", name="새마을 MCP 안내", mime_type="application/json")
    def resource_overview() -> str:
        return json.dumps(saemaul_overview(), ensure_ascii=False, indent=2)

    @mcp.resource("saemaul://sources", name="출처 레지스트리", mime_type="application/json")
    def resource_sources() -> str:
        return json.dumps(
            {"meta": corpus.registry.get("meta"), "sources": corpus.sources, "excluded": corpus.excluded},
            ensure_ascii=False,
            indent=2,
        )

    @mcp.resource("saemaul://document/{document_id}", name="문서 전문", mime_type="text/markdown")
    def resource_document(document_id: str) -> str:
        doc = corpus.document(document_id)
        if doc is None:
            return f"# {document_id}\n\n해당 문서가 없습니다. 보유 문서: {', '.join(corpus.documents)}"
        return render_markdown(doc)

    @mcp.prompt(name="saemaul_research", description="한 주제를 1차 기록과 반론까지 함께 조사한다.")
    def prompt_research(topic: str) -> str:
        return (
            f"새마을 MCP로 '{topic}'을(를) 조사한다.\n"
            "1. saemaul_search로 원문 단락과 서지를 함께 본다.\n"
            "2. 쓸 만한 단락은 saemaul_read_passage로 문맥과 관련 연구까지 확인한다.\n"
            "3. saemaul_compare_stances로 비판 쪽 출처를 반드시 함께 읽는다.\n"
            "4. 답에는 단락 citation과 출처 id를 붙이고, needs_check 상태를 밝힌다.\n"
            "도구가 돌려주지 않은 자료, 번호, 인용문은 쓰지 않는다."
        )

    @mcp.prompt(name="saemaul_check_claim", description="새마을운동에 관한 주장을 이 저장소의 근거로 검증한다.")
    def prompt_check_claim(claim: str) -> str:
        return (
            f"다음 주장을 이 저장소의 자료만으로 검증한다: \"{claim}\"\n"
            "- 뒷받침하는 단락·출처와 반박하는 단락·출처를 모두 찾는다.\n"
            "- 어느 쪽도 없으면 '이 저장소의 자료로는 판단할 수 없다'고 답한다.\n"
            "- 1차 기록은 의도를 보여 줄 뿐 결과를 입증하지 않는다는 점을 구분해 쓴다.\n"
            "- 각 근거에 citation 또는 출처 id와 verify_status를 붙인다."
        )

    return mcp


def render_markdown(doc: Document) -> str:
    """문서 하나를 사람이 읽는 마크다운으로."""
    meta = doc.meta
    lines = [f"# {meta.get('title')}", ""]
    byline = " · ".join(
        str(v) for v in (meta.get("author"), meta.get("date"), meta.get("place"), meta.get("holder")) if v
    )
    if byline:
        lines += [byline, ""]
    if meta.get("significance"):
        lines += [str(meta["significance"]).strip(), ""]
    transcription = meta.get("transcription") or {}
    rights = meta.get("rights") or {}
    lines += [
        f"> 판독 상태: {transcription.get('verify_status')} · 권리 상태: {rights.get('status')} · "
        f"스캔: {(meta.get('scan') or {}).get('file')}",
        "",
    ]
    by_section: dict[str, list] = {}
    for passage in doc.passages:
        by_section.setdefault(passage.section, []).append(passage)
    for section in doc.sections:
        number = str(section.get("number"))
        lines += [f"## {number}. {section.get('heading') or ''}".rstrip(), ""]
        for passage in by_section.get(number, []):
            if passage.kind == "heading":
                continue
            prefix = f"**{passage.label}** " if passage.label else ""
            lines += [f"{prefix}{passage.text}", f"<!-- {passage.id} · {passage.citation} -->", ""]
    if doc.glossary:
        lines += ["## 참고 어휘", ""]
        lines += [f"- **{item['term']}**: {item['meaning']}" for item in doc.glossary]
        lines += [""]
    return "\n".join(lines)

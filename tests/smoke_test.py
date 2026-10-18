#!/usr/bin/env python3
"""실제 MCP 클라이언트로 서버를 띄워 보고 도구를 하나씩 불러 본다.

Spawns the server over stdio exactly as an agent would, then calls every tool.

    python3 tests/smoke_test.py

성공하면 마지막 줄에 PASS 가 찍힌다. 실패하면 0이 아닌 코드로 끝난다.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    mark = "ok  " if condition else "FAIL"
    print(f"  [{mark}] {label}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def payload(result) -> dict:
    if getattr(result, "structuredContent", None):
        content = result.structuredContent
        return content.get("result", content) if isinstance(content, dict) else content
    for block in result.content:
        if getattr(block, "type", "") == "text":
            try:
                return json.loads(block.text)
            except json.JSONDecodeError:
                return {"text": block.text}
    return {}


async def run() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(ROOT / "saemaul_mcp_server.py")],
        env={"PYTHONPATH": str(ROOT / "src")},
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        init = await session.initialize()
        print(f"서버: {init.serverInfo.name} {init.serverInfo.version}")
        check("instructions 제공", bool(init.instructions))

        tools = await session.list_tools()
        names = sorted(t.name for t in tools.tools)
        print(f"도구 {len(names)}개: {', '.join(names)}")
        expected = {
            "saemaul_overview",
            "saemaul_search",
            "saemaul_list_documents",
            "saemaul_get_document",
            "saemaul_read_passage",
            "saemaul_find_sources",
            "saemaul_get_source",
            "saemaul_compare_stances",
            "saemaul_list_topics",
            "saemaul_editorial_notes",
        }
        check("도구가 모두 등록됨", expected <= set(names), str(sorted(expected - set(names))))
        check("모든 도구에 설명이 있음", all(t.description for t in tools.tools))

        print("\n[도구 호출]")
        overview = payload(await session.call_tool("saemaul_overview", {}))
        check("overview: 문서 포함", bool(overview.get("documents")))
        check("overview: 한계 명시", bool(overview.get("limits")))

        found = payload(await session.call_tool("saemaul_search", {"query": "자발성"}))
        check("search: 원문 단락 반환", found.get("passage_count", 0) > 0)
        check("search: 서지 반환", found.get("source_count", 0) > 0)
        first = (found.get("passages") or [{}])[0]
        check("search: citation 포함", bool(first.get("citation")), str(first))

        read_back = payload(
            await session.call_tool(
                "saemaul_read_passage",
                {"document_id": first.get("document_id", ""), "passage_id": first.get("passage_id", "")},
            )
        )
        check("read_passage: cite_as 제공", bool(read_back.get("cite_as")))
        check("read_passage: 관련 연구 연결", bool(read_back.get("cross_reference")))

        by_ref = payload(
            await session.call_tool(
                "saemaul_read_passage", {"document_id": "DOC-1972-0426", "passage_id": "§10-(4)"}
            )
        )
        check("read_passage: 인용 표기로도 조회", by_ref.get("passage", {}).get("passage_id") == "p068", str(by_ref)[:120])

        doc = payload(await session.call_tool("saemaul_get_document", {"document_id": "DOC-1972-0426"}))
        check("get_document: 목차 제공", len(doc.get("outline") or []) == 10)
        check("get_document: 권리 상태 노출", bool(doc.get("rights")))

        section = payload(
            await session.call_tool("saemaul_get_document", {"document_id": "DOC-1972-0426", "section": "6"})
        )
        check("get_document: 장 전문", len(section.get("section", {}).get("passages") or []) >= 2)

        stances = payload(await session.call_tool("saemaul_compare_stances", {"topic": "모델이전가능성"}))
        check("compare_stances: 비판 출처 반환", len(stances.get("critical") or []) >= 2)

        sources = payload(await session.call_tool("saemaul_find_sources", {"stance": "critical"}))
        check("find_sources: 관점 필터", sources.get("count", 0) >= 5)

        bad = payload(await session.call_tool("saemaul_find_sources", {"stance": "nope"}))
        check("find_sources: 잘못된 값은 오류로 안내", "error" in bad and "allowed_stance" in bad)

        one = payload(await session.call_tool("saemaul_get_source", {"source_id": "SRC-PRI-005"}))
        check("get_source: 문서 연결", one.get("document", {}).get("document_id") == "DOC-1972-0426")

        notes = payload(await session.call_tool("saemaul_editorial_notes", {}))
        check("editorial_notes: 제외 목록", notes.get("excluded_count", 0) >= 1)
        check("editorial_notes: 권리 상태", bool(notes.get("document_rights")))

        topics = payload(await session.call_tool("saemaul_list_topics", {}))
        check("list_topics: 태그 수", topics.get("count", 0) > 20)

        missing = payload(await session.call_tool("saemaul_get_source", {"source_id": "SRC-NOPE"}))
        check("없는 id는 오류와 힌트", "error" in missing and "hint" in missing)

        print("\n[리소스]")
        resources = await session.list_resources()
        templates = await session.list_resource_templates()
        uris = {str(r.uri) for r in resources.resources}
        check("고정 리소스 등록", {"saemaul://overview", "saemaul://sources"} <= uris, str(uris))
        check("문서 리소스 템플릿 등록", any("document" in t.uriTemplate for t in templates.resourceTemplates))
        body = await session.read_resource("saemaul://document/DOC-1972-0426")
        text = body.contents[0].text
        check("문서 리소스 본문", "새마을 정신" in text and len(text) > 4000, f"{len(text)}자")

        print("\n[프롬프트]")
        prompts = await session.list_prompts()
        prompt_names = {p.name for p in prompts.prompts}
        check("프롬프트 등록", {"saemaul_research", "saemaul_check_claim"} <= prompt_names, str(prompt_names))
        rendered = await session.get_prompt("saemaul_research", {"topic": "자발성"})
        check("프롬프트 렌더링", "자발성" in rendered.messages[0].content.text)


def main() -> int:
    asyncio.run(run())
    print()
    if FAILURES:
        print(f"FAIL {len(FAILURES)}건: {', '.join(FAILURES)}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

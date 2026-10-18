"""명령줄 진입점. / Command line entry point.

    saemaul-mcp                      stdio (기본). 에이전트가 이 명령을 실행한다.
    saemaul-mcp --transport http     URL로 붙는 클라이언트용
    saemaul-mcp --check              데이터를 읽어 개수만 확인하고 끝낸다
    saemaul-mcp --search 자발성      서버 없이 바로 검색해 본다
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .corpus import Corpus, CorpusError

TRANSPORTS = {
    "stdio": "stdio",
    "http": "streamable-http",
    "streamable-http": "streamable-http",
    "sse": "sse",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="saemaul-mcp",
        description="새마을운동 자료 MCP 서버 / Saemaul Undong research MCP server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--transport",
        choices=sorted(TRANSPORTS),
        default="stdio",
        help="stdio(기본)는 로컬 에이전트용, http는 URL로 붙는 클라이언트용",
    )
    parser.add_argument("--host", default="127.0.0.1", help="http 전송에서 바인드할 주소")
    parser.add_argument("--port", type=int, default=8765, help="http 전송 포트")
    parser.add_argument("--data", type=Path, default=None, help="data 폴더 경로 (기본: 저장소의 data/)")
    parser.add_argument("--check", action="store_true", help="데이터를 읽어 상태만 출력하고 끝낸다")
    parser.add_argument("--search", metavar="QUERY", help="서버를 띄우지 않고 검색 결과를 출력한다")
    parser.add_argument("--json", action="store_true", help="--check/--search 결과를 JSON으로 출력")
    return parser


def _check(corpus: Corpus, as_json: bool) -> int:
    stats = corpus.stats()
    unverified = sum(1 for s in corpus.sources if s.get("verify_status") == "needs_check")
    report = {
        "data_dir": str(corpus.data_dir),
        "registry": str(corpus.registry_path),
        "registry_version": (corpus.registry.get("meta") or {}).get("registry_version"),
        **stats,
        "unverified_sources": unverified,
        "topics": len(corpus.topics()),
        "aliases": len(corpus.aliases),
        "status": "ok",
    }
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    for key, value in report.items():
        print(f"{key}: {value}")
    for doc in corpus.documents.values():
        scan = (doc.meta.get("scan") or {}).get("file")
        exists = "있음" if scan and (corpus.root / scan).is_file() else "없음"
        print(f"  - {doc.id}: 단락 {len(doc.passages)}개, 스캔 {exists}")
    return 0


def _search(corpus: Corpus, query: str, as_json: bool) -> int:
    from .search import search_passages, search_sources

    passages = [h.payload for h in search_passages(corpus, query, limit=5)]
    sources = [h.payload for h in search_sources(corpus, query, limit=5)]
    if as_json:
        print(json.dumps({"query": query, "passages": passages, "sources": sources}, ensure_ascii=False, indent=2))
        return 0
    print(f"검색어: {query}\n")
    print(f"원문 단락 {len(passages)}건")
    for item in passages:
        print(f"  [{item['citation']}] {item['text']}")
    print(f"\n서지 출처 {len(sources)}건")
    for item in sources:
        print(f"  [{item['id']}] {item.get('title')} ({item.get('stance')}, {item.get('verify_status')})")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.data:
        os.environ["SAEMAUL_DATA"] = str(args.data)
    try:
        corpus = Corpus(args.data)
    except CorpusError as exc:
        print(f"[saemaul-mcp] {exc}", file=sys.stderr)
        return 1

    if args.check:
        return _check(corpus, args.json)
    if args.search:
        return _search(corpus, args.search, args.json)

    from .server import build_server

    transport = TRANSPORTS[args.transport]
    server = build_server(host=args.host, port=args.port)
    if transport != "stdio":
        suffix = "/mcp" if transport == "streamable-http" else "/sse"
        # stdout은 MCP 프로토콜 전용이다. 안내는 반드시 stderr로 보낸다.
        print(f"[saemaul-mcp] MCP URL: http://{args.host}:{args.port}{suffix}", file=sys.stderr)
    server.run(transport=transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

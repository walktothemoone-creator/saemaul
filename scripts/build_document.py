#!/usr/bin/env python3
"""판독문(.transcript.txt)을 구조화 문서(.yaml)로 변환한다.

Convert a plain-text transcript into the structured document YAML the server reads.

사용법 / Usage:
    python3 scripts/build_document.py data/documents/DOC-1972-0426.transcript.txt

판독문 규칙 / transcript conventions
    [제목]              첫 줄, 문서 제목
    1972.4.26. (광주)   둘째 줄, 날짜와 장소
    1. ... / 7. ...     장(section) 제목
    가. 나. 다.         절(subsection) 제목
    (1) (2) (3)         항(item)
    - ...               앞 단락에 이어지는 열거
    ---                 본문 끝. 이후는 [참고 어휘 설명] 용어풀이
    (*) 낱말: 뜻        용어풀이 한 줄

본문의 한 줄이 한 단락(passage)이 된다. 단락마다 바뀌지 않는 id(p001...)와
사람이 읽는 인용 표기(§7-나-(2))를 함께 붙인다. 원문 라벨은 그대로 보존한다.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path
from typing import Any

import yaml

SUBSECTION_LETTERS = {"가": "a", "나": "b", "다": "c", "라": "d", "마": "e", "바": "f"}

RE_TITLE = re.compile(r"^\[(?P<title>.+)\]$")
RE_DATELINE = re.compile(r"^(?P<date>\d{4})\.(?P<month>\d{1,2})\.(?P<day>\d{1,2})\.?\s*(?:\((?P<place>.+)\))?$")
RE_SECTION = re.compile(r"^(?P<num>\d{1,2})[.\s]\s*(?P<rest>.*)$")
RE_SUBSECTION = re.compile(r"^(?P<letter>[가-바])\.\s*(?P<rest>.+)$")
RE_ITEM = re.compile(r"^\((?P<num>\d{1,2})\)\s*(?P<rest>.*)$")
RE_BULLET = re.compile(r"^\s*[-예]\s*[:．.]?\s*")
RE_GLOSSARY = re.compile(r"^\(\*\)\s*(?P<term>[^:：]+)[:：]\s*(?P<meaning>.+)$")

HANJA = re.compile(r"\(([一-鿿㐀-䶿][^)]*)\)")


def strip_hanja(text: str) -> str:
    """한자 병기를 뺀 한글 표면형. 검색 색인에 함께 넣는다."""
    return re.sub(r"\s+", " ", HANJA.sub("", text)).strip()


def hanja_terms(text: str) -> list[str]:
    return sorted({m.group(1).strip() for m in HANJA.finditer(text) if m.group(1).strip()})


class Builder:
    def __init__(self) -> None:
        self.title = ""
        self.date = ""
        self.place = ""
        self.sections: list[dict[str, Any]] = []
        self.glossary: list[dict[str, str]] = []
        self.passages: list[dict[str, Any]] = []
        self._section: dict[str, Any] | None = None
        self._subsection: str = ""
        self._last: dict[str, Any] | None = None

    # ------------------------------------------------------------------ parse
    def feed_body(self, line: str) -> None:
        if match := RE_SECTION.match(line):
            num = match.group("num")
            rest = match.group("rest").strip()
            self._open_section(num, rest)
            if rest and (item := RE_ITEM.match(rest)):
                self._add(label=f"({item.group('num')})", text=item.group("rest").strip())
            elif rest:
                # 장 머리글도 본문이다. 검색되도록 단락으로 함께 남긴다.
                self._add(label="", text=rest, kind="heading")
            return

        if self._section is not None and (match := RE_SUBSECTION.match(line)):
            letter = match.group("letter")
            self._subsection = letter
            self._add(label=f"{letter}.", text=match.group("rest").strip(), kind="subsection")
            return

        if match := RE_ITEM.match(line):
            self._add(label=f"({match.group('num')})", text=match.group("rest").strip())
            return

        if RE_BULLET.match(line) and self._last is not None:
            self._last["text"] += "\n" + line.strip()
            return

        self._add(label="", text=line.strip())

    def _open_section(self, num: str, heading: str) -> None:
        display = heading if not RE_ITEM.match(heading) else ""
        self._section = {"number": num, "heading": display, "passages": []}
        self._subsection = ""
        self.sections.append(self._section)
        self._last = None

    def _add(self, label: str, text: str, kind: str = "passage") -> None:
        if not text:
            return
        if self._section is None:
            self._open_section("0", "")
        section_no = self._section["number"]
        parts = [f"§{section_no}"]
        if self._subsection and kind != "subsection":
            parts.append(SUBSECTION_LETTERS.get(self._subsection, self._subsection))
        elif kind == "subsection":
            parts.append(SUBSECTION_LETTERS.get(self._subsection, self._subsection))
        if label and not label.endswith("."):
            parts.append(label)
        ref = "-".join(parts)
        passage = {
            "id": f"p{len(self.passages) + 1:03d}",
            "kind": kind,
            "ref": ref,
            "section": section_no,
            "section_heading": self._section["heading"],
            "label": label,
            "text": text,
        }
        self.passages.append(passage)
        self._section["passages"].append(passage["id"])
        self._last = passage

    def feed_glossary(self, line: str) -> None:
        if match := RE_GLOSSARY.match(line):
            self.glossary.append(
                {"term": match.group("term").strip(), "meaning": match.group("meaning").strip()}
            )

    # ----------------------------------------------------------------- output
    def enrich(self) -> None:
        for passage in self.passages:
            plain = strip_hanja(passage["text"])
            if plain and plain != passage["text"]:
                passage["text_plain"] = plain
            terms = hanja_terms(passage["text"])
            if terms:
                passage["hanja"] = terms


def parse(path: Path) -> Builder:
    builder = Builder()
    in_glossary = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.strip() == "---":
            in_glossary = True
            continue
        if in_glossary:
            if line.startswith("["):
                continue
            builder.feed_glossary(line)
            continue
        if match := RE_TITLE.match(line.strip()):
            builder.title = match.group("title").strip()
            continue
        if not builder.date and (match := RE_DATELINE.match(line.strip())):
            builder.date = (
                f"{match.group('date')}-{int(match.group('month')):02d}-{int(match.group('day')):02d}"
            )
            builder.place = strip_hanja(match.group("place") or "")
            continue
        builder.feed_body(line)
    builder.enrich()
    return builder


def to_document(builder: Builder, doc_id: str, meta_path: Path | None) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    if meta_path and meta_path.is_file():
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
    overrides = meta.pop("section_headings", None) or {}
    for section in builder.sections:
        override = overrides.get(section["number"]) or overrides.get(int(section["number"]))
        if override:
            section["heading"] = override
    if overrides:
        by_number = {s["number"]: s["heading"] for s in builder.sections}
        for passage in builder.passages:
            passage["section_heading"] = by_number.get(passage["section"], passage["section_heading"])
    document: dict[str, Any] = {
        "id": doc_id,
        "title": meta.get("title") or builder.title,
        "date": meta.get("date") or builder.date,
        "place": meta.get("place") or builder.place,
    }
    document.update({k: v for k, v in meta.items() if k not in document})
    document["generated_at"] = dt.date.today().isoformat()
    document["sections"] = [
        {"number": s["number"], "heading": s["heading"], "passages": s["passages"]}
        for s in builder.sections
        if s["passages"]
    ]
    document["passages"] = builder.passages
    if builder.glossary:
        document["glossary"] = builder.glossary
    return document


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("transcript", type=Path, help="판독문 .transcript.txt 경로")
    parser.add_argument("--meta", type=Path, default=None, help="서지 메타 YAML (기본: 같은 이름의 .meta.yaml)")
    parser.add_argument("--out", type=Path, default=None, help="출력 경로 (기본: 같은 이름의 .yaml)")
    args = parser.parse_args()

    transcript: Path = args.transcript
    if not transcript.is_file():
        sys.exit(f"판독문을 찾을 수 없습니다: {transcript}")
    doc_id = transcript.name.split(".")[0]
    meta_path = args.meta or transcript.with_name(f"{doc_id}.meta.yaml")
    out_path = args.out or transcript.with_name(f"{doc_id}.yaml")

    builder = parse(transcript)
    document = to_document(builder, doc_id, meta_path)
    out_path.write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    print(f"{out_path}: 장 {len(document['sections'])}개, 단락 {len(document['passages'])}개, "
          f"용어 {len(document.get('glossary', []))}개")


if __name__ == "__main__":
    main()

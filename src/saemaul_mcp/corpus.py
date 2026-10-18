"""데이터 적재와 색인. / Loading and indexing.

data/ 아래 세 가지를 읽는다.
  sources.yaml           서지 레지스트리 (무엇을 어디서 볼지)
  documents/*.yaml       전문을 보유한 문서 (단락 단위 인용 가능)
  search_aliases.yaml    검색어 확장 사전 (없어도 동작한다)

순수 파이썬 + PyYAML 만 쓴다. 외부 검색 엔진이나 모델에 의존하지 않는다.
"""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

STANCES = ("supportive", "critical", "analytical", "foundational")
LAYERS = ("primary", "scholarly", "theory", "ontology", "infra")
VERIFY_STATUSES = ("url_verified", "needs_check")
RELATIONS = ("interprets", "contested_by", "corroborates")

SOURCE_SUMMARY_KEYS = (
    "id",
    "layer",
    "title",
    "authors",
    "year",
    "stance",
    "theoretical_framework",
    "url",
    "verify_status",
    "document_id",
    "use_for",
)
SOURCE_SEARCH_KEYS = SOURCE_SUMMARY_KEYS + (
    "holder",
    "journal",
    "publisher",
    "note",
    "key_claims",
    "scope_note",
    "volume",
    "pages",
)

_HANJA_PARENS = re.compile(r"\(([一-鿿㐀-䶿][^)]*)\)")
_WORD = re.compile(r"[0-9A-Za-z가-힣一-鿿㐀-䶿]+")


class CorpusError(RuntimeError):
    """데이터를 읽을 수 없을 때."""


# --------------------------------------------------------------------- 정규화
def normalize(text: str) -> str:
    """대소문자·공백·문장부호 차이를 지운 비교용 표면형."""
    folded = unicodedata.normalize("NFKC", text).casefold()
    return "".join(_WORD.findall(folded))


@dataclass(slots=True, frozen=True)
class Haystack:
    """찾을 대상 문자열과, 각 글자가 낱말 첫 글자인지의 표시.

    공백을 지워야 "새마을 운동"과 "새마을운동"이 같게 걸린다.
    그런데 그렇게만 하면 "분석하여 성과"가 "여성"에 걸리는 일이 생긴다.
    낱말 첫 글자 위치를 따로 들고 있다가, 낱말 중간에서 걸린 짧은 말은 약하게 친다.
    """

    text: str
    starts: frozenset[int]

    def __bool__(self) -> bool:
        return bool(self.text)


def build_haystack(*parts: Any) -> Haystack:
    pieces: list[str] = []
    starts: list[int] = []
    cursor = 0
    for part in parts:
        for word in _WORD.findall(unicodedata.normalize("NFKC", as_text(part)).casefold()):
            starts.append(cursor)
            pieces.append(word)
            cursor += len(word)
    return Haystack(text="".join(pieces), starts=frozenset(starts))


def tokenize(text: str) -> list[str]:
    return [t for t in _WORD.findall(unicodedata.normalize("NFKC", text).casefold()) if t]


def strip_hanja(text: str) -> str:
    return re.sub(r"\s+", " ", _HANJA_PARENS.sub("", text)).strip()


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return " ".join(as_text(v) for v in value)
    if isinstance(value, dict):
        return " ".join(as_text(v) for v in value.values())
    return str(value)


# ----------------------------------------------------------------- 자료 구조
@dataclass(slots=True)
class Passage:
    doc_id: str
    id: str
    ref: str
    section: str
    section_heading: str
    label: str
    kind: str
    text: str
    haystack: "Haystack" = field(repr=False, default_factory=lambda: Haystack("", frozenset()))

    @property
    def citation(self) -> str:
        return f"{self.doc_id} {self.ref}"

    def summary(self, snippet: str | None = None) -> dict[str, Any]:
        out: dict[str, Any] = {
            "document_id": self.doc_id,
            "passage_id": self.id,
            "citation": self.citation,
            "section": self.section,
            "section_heading": self.section_heading,
        }
        out["text"] = snippet if snippet is not None else self.text
        return out


@dataclass(slots=True)
class Document:
    id: str
    meta: dict[str, Any]
    sections: list[dict[str, Any]]
    passages: list[Passage]
    glossary: list[dict[str, str]]
    cross_references: dict[str, dict[str, Any]]

    def passage(self, passage_id: str) -> Passage | None:
        wanted = passage_id.strip().casefold()
        for passage in self.passages:
            if passage.id.casefold() == wanted or passage.ref.casefold() == wanted:
                return passage
        # §7-나-(2) 처럼 한글 절 기호로 들어온 경우를 받아 준다.
        loose = normalize(passage_id)
        for passage in self.passages:
            if normalize(passage.ref) == loose:
                return passage
        return None

    def card(self) -> dict[str, Any]:
        """목록에 쓰는 요약. 본문은 넣지 않는다."""
        meta = self.meta
        return {
            "document_id": self.id,
            "title": meta.get("title"),
            "title_en": meta.get("title_en"),
            "author": meta.get("author"),
            "date": meta.get("date"),
            "place": meta.get("place"),
            "kind": meta.get("kind"),
            "holder": meta.get("holder"),
            "passages": len(self.passages),
            "sections": len(self.sections),
            "topics": meta.get("topics") or [],
            "significance": (meta.get("significance") or "").strip() or None,
            "source_id": meta.get("source_id"),
            "transcription_status": (meta.get("transcription") or {}).get("verify_status"),
            "rights_status": (meta.get("rights") or {}).get("status"),
            "scan": (meta.get("scan") or {}).get("file"),
        }


# --------------------------------------------------------------------- 적재
def _require_yaml():
    try:
        import yaml  # noqa: PLC0415
    except ModuleNotFoundError as exc:  # pragma: no cover - 설치 안내용
        raise CorpusError(
            "PyYAML이 필요합니다. `pip install -r requirements.txt` 또는 `uv run` 으로 실행하세요."
        ) from exc
    return yaml


def _read_yaml(path: Path) -> Any:
    yaml = _require_yaml()
    try:
        with path.open(encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except OSError as exc:
        raise CorpusError(f"파일을 읽을 수 없습니다: {path} ({exc})") from exc
    except Exception as exc:  # yaml.YAMLError
        raise CorpusError(f"YAML 형식이 올바르지 않습니다: {path} ({exc})") from exc


def default_data_dir() -> Path:
    """data 폴더를 찾는다. 저장소에서 바로 실행하든, 설치해서 쓰든 같게 동작하게.

    순서: SAEMAUL_DATA 환경 변수 → 패키지에 함께 설치된 data →
          저장소 뿌리의 data → 현재 작업 폴더의 data
    """
    env = os.environ.get("SAEMAUL_DATA")
    if env:
        return Path(env).expanduser().resolve()
    here = Path(__file__).resolve()
    candidates = [
        here.parent / "data",          # pip/uvx 로 설치된 경우
        here.parents[2] / "data",      # 저장소를 그대로 받아 실행하는 경우
        Path.cwd() / "data",
    ]
    for candidate in candidates:
        if (candidate / "sources.yaml").is_file():
            return candidate.resolve()
    return candidates[1].resolve()


class Corpus:
    """레지스트리와 문서를 메모리에 올린 읽기 전용 모음."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = (data_dir or default_data_dir()).resolve()
        self.root = self.data_dir.parent
        if not self.data_dir.is_dir():
            raise CorpusError(
                f"데이터 폴더를 찾을 수 없습니다: {self.data_dir}\n"
                "저장소 안에서 실행하거나 SAEMAUL_DATA 환경 변수로 경로를 지정하세요."
            )
        self.registry = self._load_registry()
        self.sources: list[dict[str, Any]] = self.registry.get("sources") or []
        self.excluded: list[dict[str, Any]] = self.registry.get("excluded") or []
        self.aliases = self._load_aliases()
        self.documents = self._load_documents()
        self._source_by_id = {str(s.get("id")): s for s in self.sources}
        self._source_haystack = {
            str(s.get("id")): build_haystack(*(s.get(k) for k in SOURCE_SEARCH_KEYS))
            for s in self.sources
        }
        self._document_haystack = {
            doc.id: build_haystack(
                doc.id,
                doc.meta.get("title"),
                doc.meta.get("title_en"),
                doc.meta.get("author"),
                doc.meta.get("date"),
                doc.meta.get("place"),
                doc.meta.get("kind"),
                doc.meta.get("holder"),
                doc.meta.get("topics"),
                doc.meta.get("significance"),
            )
            for doc in self.documents.values()
        }
        self._link_documents()

    # ------------------------------------------------------------ 적재 단계
    def _load_registry(self) -> dict[str, Any]:
        path = Path(os.environ.get("SAEMAUL_REGISTRY") or self.data_dir / "sources.yaml")
        if not path.is_file():
            raise CorpusError(f"출처 레지스트리를 찾을 수 없습니다: {path}")
        data = _read_yaml(path)
        if not isinstance(data, dict) or not isinstance(data.get("sources"), list):
            raise CorpusError(f"레지스트리에 sources 목록이 없습니다: {path}")
        self.registry_path = path
        return data

    def _load_aliases(self) -> dict[str, set[str]]:
        path = self.data_dir / "search_aliases.yaml"
        if not path.is_file():
            return {}
        raw = (_read_yaml(path) or {}).get("aliases") or {}
        table: dict[str, set[str]] = {}
        for key, values in raw.items():
            group = {normalize(str(key))} | {normalize(str(v)) for v in (values or [])}
            group.discard("")
            for member in group:
                table.setdefault(member, set()).update(group)
        return table

    def _load_documents(self) -> dict[str, Document]:
        docs: dict[str, Document] = {}
        folder = self.data_dir / "documents"
        if not folder.is_dir():
            return docs
        for path in sorted(folder.glob("*.yaml")):
            if path.name.endswith(".meta.yaml"):
                continue
            raw = _read_yaml(path)
            if not isinstance(raw, dict) or not raw.get("id"):
                raise CorpusError(f"문서에 id가 없습니다: {path}")
            doc = self._build_document(raw)
            docs[doc.id] = doc
        return docs

    def _build_document(self, raw: dict[str, Any]) -> Document:
        doc_id = str(raw["id"])
        passages: list[Passage] = []
        for item in raw.get("passages") or []:
            text = str(item.get("text") or "")
            passage = Passage(
                doc_id=doc_id,
                id=str(item.get("id")),
                ref=str(item.get("ref") or item.get("id")),
                section=str(item.get("section") or ""),
                section_heading=str(item.get("section_heading") or ""),
                label=str(item.get("label") or ""),
                kind=str(item.get("kind") or "passage"),
                text=text,
            )
            passage.haystack = build_haystack(
                text,
                strip_hanja(text),
                item.get("hanja"),
                passage.section_heading,
                strip_hanja(passage.section_heading),
                passage.ref,
            )
            passages.append(passage)

        cross: dict[str, dict[str, Any]] = {}
        for entry in raw.get("cross_references") or []:
            key = str(entry.get("passage") or "")
            if key:
                cross[key] = {
                    "note": entry.get("note"),
                    "links": entry.get("links") or [],
                }

        meta = {k: v for k, v in raw.items() if k not in {"passages", "sections", "glossary", "cross_references"}}
        return Document(
            id=doc_id,
            meta=meta,
            sections=raw.get("sections") or [],
            passages=passages,
            glossary=raw.get("glossary") or [],
            cross_references=cross,
        )

    def _link_documents(self) -> None:
        """레지스트리의 document_id 와 문서의 source_id 를 양쪽으로 잇는다."""
        for source in self.sources:
            doc_id = source.get("document_id")
            if doc_id and doc_id in self.documents:
                self.documents[doc_id].meta.setdefault("source_id", source.get("id"))

    # ------------------------------------------------------------- 조회 보조
    def source(self, source_id: str) -> dict[str, Any] | None:
        return self._source_by_id.get(source_id) or self._source_by_id.get(source_id.upper())

    def source_summary(self, source: dict[str, Any]) -> dict[str, Any]:
        return {k: source[k] for k in SOURCE_SUMMARY_KEYS if source.get(k) is not None}

    def document(self, doc_id: str) -> Document | None:
        if doc_id in self.documents:
            return self.documents[doc_id]
        wanted = normalize(doc_id)
        for key, doc in self.documents.items():
            if normalize(key) == wanted:
                return doc
        return None

    def topics(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for source in self.sources:
            for topic in source.get("use_for") or []:
                counts[str(topic)] = counts.get(str(topic), 0) + 1
        for doc in self.documents.values():
            for topic in doc.meta.get("topics") or []:
                counts[str(topic)] = counts.get(str(topic), 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))

    def expand(self, token: str) -> set[str]:
        """검색어 하나를 동의어까지 넓힌다."""
        key = normalize(token)
        if not key:
            return set()
        return self.aliases.get(key, {key}) | {key}

    def all_passages(self) -> Iterable[Passage]:
        for doc in self.documents.values():
            yield from doc.passages

    def source_haystack(self, source_id: str) -> Haystack:
        return self._source_haystack.get(source_id) or Haystack("", frozenset())

    def document_haystack(self, document_id: str) -> Haystack:
        return self._document_haystack.get(document_id) or Haystack("", frozenset())

    def stats(self) -> dict[str, Any]:
        layers: dict[str, int] = {}
        stances: dict[str, int] = {}
        for source in self.sources:
            layers[str(source.get("layer") or "unknown")] = layers.get(str(source.get("layer") or "unknown"), 0) + 1
            stances[str(source.get("stance") or "unknown")] = stances.get(str(source.get("stance") or "unknown"), 0) + 1
        return {
            "sources": len(self.sources),
            "excluded": len(self.excluded),
            "documents": len(self.documents),
            "passages": sum(len(d.passages) for d in self.documents.values()),
            "layers": layers,
            "stances": stances,
        }

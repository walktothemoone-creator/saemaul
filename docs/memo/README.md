# 변경 기록 체계

이 저장소는 끝나지 않습니다. 그래서 **모든 변경을 기록으로 남깁니다.** 이 폴더가 그 기록이 쌓이는
한 곳이고, 이 문서가 그 규격입니다.

기록하는 방법은 [`../../git_change_memo_skill.md`](../../git_change_memo_skill.md)에 있습니다.
에이전트는 파일을 고친 뒤 그 절차를 따릅니다.

```
docs/memo/
├── README.md                      ← 이 문서. 규격
├── CHANGELOG.md                   ← 누적 역사. 릴리스 단위로 읽는다
└── YYYY-MM-DD-NNN-<슬러그>.md      ← 변경 하나당 메모. 왜 바꿨는지가 여기에 있다
```

두 층으로 나눈 이유가 있습니다. `CHANGELOG.md`는 **무엇이 달라졌는지 훑는 곳**이고, 메모는
**왜 그렇게 바꿨고 무엇을 확인했는지 되짚는 곳**입니다. 둘을 한 파일에 담으면 전자는 길어서 못 읽고
후자는 짧아서 쓸모가 없어집니다.

---

## 1. 메모 파일

### 이름

`YYYY-MM-DD-NNN-<슬러그>.md`

- `NNN` — 그날의 순번. `001`부터.
- `<슬러그>` — 영소문자와 하이픈. 무엇을 건드렸는지 알아볼 수 있게.
- 예: `2026-10-18-002-memo-system.md`

### 형식

```markdown
---
memo: 2026-10-18-001
date: 2026-10-18
area: docs            # data | code | docs | ci | meta
impact: minor         # major | minor | patch
by: agent             # agent | human
---

# <한 줄 제목>

## 무엇이 바뀌었나
## 왜 바꿨나
## 바꾼 파일
## 확인한 것
## 짝 문서
## 되돌리려면
```

`왜 바꿨나`가 이 체계의 전부입니다. 파일 목록은 `git log`에 이미 있습니다. 거기에 없는 것, 곧
**판단의 근거**를 적으십시오.

### area — 어디가 바뀌었나

| area | 범위 |
|---|---|
| `data` | `data/` 전부. 판독문, 서지 메타, 출처 레지스트리, 검색어 사전, 스캔 |
| `code` | `src/`, `saemaul_mcp_server.py`, `scripts/`, `tests/` |
| `docs` | `docs/`, `README*.md`, `CONTRIBUTING.md`, `NOTICE.md` |
| `ci` | `.github/`, `examples/`, `pyproject.toml`, `requirements.txt`, `.gitignore` |
| `meta` | `docs/memo/` 자체, `git_change_memo_skill.md`, `LICENSE` |

두 군데 이상 걸치면 여러 개를 적습니다. `area: [data, docs]`

### impact — 얼마나 바뀌었나

[`../maintenance.md`](../maintenance.md)의 버전 체계와 같은 기준입니다. **에이전트가 보는 것이
깨지는가.**

| impact | 뜻 |
|---|---|
| `major` | 도구 계약이나 id 체계가 바뀌어 기존 사용이 깨진다 |
| `minor` | 더해졌다. 기존 사용은 그대로다 |
| `patch` | 고쳤다. 계약도 범위도 그대로다 |

## 2. 폴더별 기록 정책

무엇을 고치면 무엇을 함께 봐야 하는지의 표입니다. 메모의 `짝 문서` 항목은 이 표에서 나옵니다.

| 경로 | 무엇 | 메모 | 기본 impact | 반드시 함께 |
|---|---|---|---|---|
| `data/documents/*.transcript.txt` | 판독문 | 필수 | 교정 `patch` · 새 문서 `minor` | 재생성, `cross_references`의 단락 id |
| `data/documents/*.meta.yaml` | 서지·교차참조 | 필수 | `minor` | `NOTICE.md`(권리), 지지·비판 균형 |
| `data/documents/*.yaml` | **생성물** | 불필요 | — | 위 둘과 같은 커밋에 넣는다 |
| `data/sources.yaml` | 출처 레지스트리 | 필수 | `minor` | `stance` 한쪽으로 기울지 않았는지 |
| `data/search_aliases.yaml` | 검색어 사전 | 필수 | `patch` | `--search`로 오검색 확인 |
| `data/scans/` | 스캔 원본 | 필수 | `minor` | `NOTICE.md`. 권리 미확인이면 올리지 않는다 |
| `src/**`, `saemaul_mcp_server.py` | 도구 계약 | 필수 | 계약이 바뀌면 `major` | `docs/clients.md`, README의 도구 표 |
| `scripts/` | 생성기 | 필수 | 출력이 달라지면 `major` | 전체 재생성 후 diff 확인 |
| `tests/` | 검사 | 필수 | `patch` | — |
| `docs/action-theory.ko.md` · `.en.md` | 행동론 | 필수 | `minor` | **짝 언어**, 상단 날짜 |
| `docs/epilogue.md` | 에필로그 | 필수 | `patch` | 한 파일 안 두 언어 |
| `docs/clients.md`, `docs/maintenance.md` | 안내 | 필수 | `patch` | README |
| `README.ko.md` · `README.md` | 입구 | 필수 | `patch` | **짝 언어** |
| `CONTRIBUTING.md`, `NOTICE.md` | 규약·권리 | 필수 | `patch` | 바뀐 대상 폴더 |
| `.github/workflows/` | CI | 필수 | `patch` | `docs/maintenance.md` |
| `examples/` | 설정 예시 | 필수 | `patch` | `docs/clients.md` |
| `pyproject.toml`, `requirements.txt` | 의존성·버전 | 필수 | 의존성 추가 `minor` | `.github/workflows/check.yml` |
| `LICENSE` | 라이선스 | 필수 | `major` | `NOTICE.md` |
| `docs/memo/**` | 기록 자체 | **불필요** | — | 메모에 대한 메모를 쓰지 않는다 |
| `__pycache__`, `.DS_Store`, `.venv` | 쓰레기 | 커밋 금지 | — | `.gitignore`가 막는다 |

## 3. CHANGELOG.md와의 관계

메모를 하나 쓸 때마다 [`CHANGELOG.md`](CHANGELOG.md)의 `## [미출시]` 아래에 **한 줄**을 더하고,
그 메모로 링크를 겁니다.

```markdown
- 행동론을 피지컬 AI 프레임으로 다시 썼다. ([2026-10-18-001](2026-10-18-001-action-theory-physical-ai.md))
```

릴리스할 때 `[미출시]`가 버전 제목이 됩니다. 메모는 지우지 않고 그대로 쌓아 둡니다.

## 4. 지키는 것

- **지어내지 않습니다.** 확인하지 않은 것을 `확인한 것`에 적지 않습니다.
- **생성물만 바뀐 커밋에는 메모를 쓰지 않습니다.** 원본을 고친 메모가 이미 그것을 설명합니다.
- **메모를 지우지 않습니다.** 판단이 틀렸으면 새 메모에서 바로잡고 앞 메모를 링크합니다.
- **파일 목록만 적은 메모는 메모가 아닙니다.** `왜`가 없으면 `git log`와 다를 바 없습니다.

# 저장소와 문서를 관리하는 법

이 저장소는 끝나는 프로젝트가 아닙니다. 자료가 더해지고, 판독이 고쳐지고, 행동론이 다시 쓰입니다.
그래서 **무엇이 언제 어떻게 바뀌었는지 남기는 규칙**이 필요합니다. 이 문서가 그 규칙이고,
바뀐 내용 자체는 [docs/memo/](memo/README.md)에 쌓입니다. 변경 하나에 메모 하나를 남기고,
`memo/CHANGELOG.md`에 한 줄로 요약합니다. 에이전트가 따르는 절차는
[`git_change_memo_skill.md`](../git_change_memo_skill.md)에 있습니다.

자료를 더하고 고치는 방법은 [CONTRIBUTING.md](../CONTRIBUTING.md)에 있습니다. 이 문서는 그 위에서
**저장소 전체가 버전으로 관리되게** 하는 규칙만 다룹니다.

---

## 1. 버전 체계

`MAJOR.MINOR.PATCH` (유의적 버전). 올림의 기준은 하나입니다. **에이전트가 보는 것이 깨지는가.**

| 올림 | 언제 | 예 |
|---|---|---|
| MAJOR | 도구 이름·인자·응답 구조가 바뀌어 기존 클라이언트 설정이 깨진다 | 도구 인자 제거, id 체계 변경 |
| MINOR | 도구·자료·문서가 더해진다. 기존 사용법은 그대로다 | 원문 문서 추가, 도구 추가, 행동론 개정 |
| PATCH | 고치기만 한다. 계약도 범위도 그대로다 | 판독 오류 교정, 오탈자, URL 확인 |

**id는 버전과 무관하게 영구합니다.** `SRC-*`, `DOC-*`, 단락 id(`p001`…)는 한 번 공개하면 바꾸지
않습니다. 바꿔야 할 만큼 잘못됐다면 그것은 MINOR가 아니라 MAJOR입니다.

## 2. 버전이 적힌 자리

세 곳이 항상 같아야 합니다. 하나만 고치면 어긋납니다.

| 파일 | 자리 |
|---|---|
| `pyproject.toml` | `version = "…"` |
| `src/saemaul_mcp/__init__.py` | `__version__ = "…"` |
| `docs/memo/CHANGELOG.md` | 맨 위 릴리스 제목 |

```bash
grep -n '^version\|^__version__' pyproject.toml src/saemaul_mcp/__init__.py
head -20 docs/memo/CHANGELOG.md
```

## 3. 문서 대장

| 문서 | 담는 것 | 함께 고쳐야 하는 짝 |
|---|---|---|
| `README.ko.md` · `README.md` | 저장소 소개, 근본 주장, 설치, 도구 목록 | 서로 짝 |
| `docs/action-theory.ko.md` · `docs/action-theory.en.md` | 새마을행동론 전문 | 서로 짝. 절 구성까지 같게 둡니다 |
| `docs/epilogue.md` | 국·영문 에필로그 | 한 파일 안에 두 언어 |
| `docs/clients.md` | 클라이언트별 설정 | 실행법·도구 이름이 바뀌면 README와 함께 |
| `docs/maintenance.md` | 이 문서 | — |
| `CONTRIBUTING.md` | 자료를 더하고 고치는 법 | 데이터 스키마가 바뀌면 함께 |
| `NOTICE.md` | 자료 출처와 권리 | 자료가 늘면 함께 |
| `docs/memo/` | 변경 기록 — 규격, 메모, CHANGELOG | 모든 변경 |
| `git_change_memo_skill.md` | 에이전트가 기록을 남기는 절차 | `docs/memo/README.md` |
| `LICENSE` | 코드 라이선스(MIT) | — |

### 두 언어 규칙

국문과 영문이 짝인 문서는 **같은 커밋에서 같이** 고칩니다. 한쪽에만 들어간 문장은 다음 사람이
어느 쪽을 믿어야 할지 알 수 없게 만듭니다.

의도된 비대칭은 여기에 적어 둡니다. 적혀 있지 않은 차이는 빠뜨린 것입니다.

- `docs/action-theory.en.md`의 `A Note for International Readers` — 새마을운동을 모르는 독자를
  위한 절. 국문에는 두지 않습니다.
- `README.md`의 協動 풀이는 괄호 한 줄, 행동론 영문은 한 문장. 문서 성격에 따른 수위 차이입니다.

```bash
grep -c '^## ' docs/action-theory.ko.md docs/action-theory.en.md   # 절 수가 같은가
```

### 서명이 있는 글

`docs/action-theory.*`처럼 글쓴이와 날짜가 적힌 글은 내용을 고칠 때 상단 날짜도 함께 고칩니다.
그 밖의 문서는 개정 이력을 `docs/memo/` 한 곳에서만 관리합니다. 날짜를 두 곳에 두면 어긋납니다.

## 4. 고칠 때의 절차

2번과 3번은 `.github/workflows/check.yml`이 푸시·PR마다 다시 돌려 줍니다.
다만 **CI는 알려 줄 뿐 고치지 않습니다.** 4번의 기록과 5절의 버전 올림은 사람이 합니다.

1. 원문을 고쳤으면 다시 생성합니다.
   ```bash
   python3 scripts/build_document.py data/documents/<DOC-ID>.transcript.txt
   ```
2. 검사합니다.
   ```bash
   python3 saemaul_mcp_server.py --check
   python3 tests/smoke_test.py
   ```
3. 짝 문서를 같이 고쳤는지 확인합니다. (3절의 대장)
4. `docs/memo/`에 메모를 남기고 `docs/memo/CHANGELOG.md`의 `## [미출시]` 아래에 한 줄 겁니다.
   절차는 [`git_change_memo_skill.md`](../git_change_memo_skill.md)를 따릅니다.
5. 커밋합니다. 제목은 `<종류>: <무엇을 했는가>`.

| 종류 | 쓰는 때 |
|---|---|
| `data:` | 원문·출처·검색어 사전 |
| `docs:` | 문서 |
| `feat:` | 도구·기능 추가 |
| `fix:` | 버그 수정 |
| `chore:` | 버전 올림, 설정, 정리 |

### 자동으로 도는 검사

`.github/workflows/check.yml`이 Python 3.10과 3.12에서 세 가지를 봅니다.

| 검사 | 무엇을 잡는가 |
|---|---|
| `--check` | 출처·문서·검색어 사전이 서로 맞는지 |
| `tests/smoke_test.py` | 도구와 프롬프트가 실제로 뜨는지 |
| 생성물 동기화 | 판독문을 고치고 `build_document.py`를 다시 돌리지 않은 경우 |

셋째가 이 저장소에서 가장 자주 나는 사고입니다. 판독문에 줄을 더하면 그 뒤 단락 id가 전부
밀리고, `cross_references`의 `passage`가 엉뚱한 대목을 가리키게 됩니다.

## 5. 릴리스

1. `docs/memo/CHANGELOG.md`의 `[미출시]`를 새 버전 제목과 날짜로 바꾸고, 그 위에 빈 `[미출시]`를
   다시 만듭니다. 메모는 지우지 않고 그대로 쌓아 둡니다.
2. `pyproject.toml`과 `src/saemaul_mcp/__init__.py`의 버전을 같은 값으로 올립니다.
3. 커밋하고 태그를 붙입니다.
   ```bash
   python3 saemaul_mcp_server.py --check && python3 tests/smoke_test.py
   git commit -am "chore: release v0.3.0"
   git tag -a v0.3.0 -m "v0.3.0"
   ```

## 6. 이 저장소가 지키는 것

[CONTRIBUTING.md](../CONTRIBUTING.md)의 네 가지에 하나를 더합니다.

- 지어내지 않습니다. 모르면 비우고 `needs_check`로 둡니다.
- 뺀 것은 이유와 함께 남깁니다. 조용히 지우지 않습니다.
- 1차 기록은 의도를 보여 줄 뿐 결과를 입증하지 않는다는 구분을 흐리지 않습니다.
- 비판 연구를 같이 싣습니다.
- **바뀐 것은 기록합니다.** 조용히 달라진 문서는 근거가 되지 못합니다.

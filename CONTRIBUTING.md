# 자료를 더하고 고치는 법

코드를 건드릴 일은 거의 없습니다. `data/` 안의 **사람이 고치는 파일**만 수정하고 Pull Request를 보내십시오.

| 파일 | 고칩니까 |
|---|---|
| `data/sources.yaml` | 예 — 서지 출처 |
| `data/search_aliases.yaml` | 예 — 검색어 사전 |
| `data/documents/*.meta.yaml` | 예 — 서지 메타와 교차참조 |
| `data/documents/*.transcript.txt` | 예 — 판독문 |
| `data/documents/*.yaml` | **아니오** — 위 둘로 만들어지는 생성물 |

고친 뒤에는 반드시 확인합니다.

```bash
python3 scripts/build_document.py data/documents/DOC-1972-0426.transcript.txt   # 문서를 고쳤다면
python3 saemaul_mcp_server.py --check
python3 tests/smoke_test.py
```

---

## 1. 서지 출처 더하기

`data/sources.yaml`의 `sources:` 아래에 항목을 추가합니다. id는 `SRC-<층위3자>-<번호>` 형식이고,
**한 번 정한 id는 바꾸지 않습니다.** 다른 곳에서 그 id로 참조하기 때문입니다.

```yaml
  - id: SRC-SCH-008
    layer: scholarly          # primary | scholarly | theory | ontology | infra
    title: "논문 제목"
    authors: ["저자"]
    journal: "학술지"
    year: 2020
    stance: critical          # supportive | critical | analytical | foundational
    theoretical_framework: ["어떤 이론에 기대고 있는지"]
    url: "https://..."
    verify_status: url_verified   # url_verified | needs_check
    key_claims: ["이 연구가 실제로 주장하는 것"]
    use_for: [주제태그, 주제태그]
```

지켜 주십시오.

- **확인한 것만 적습니다.** 저자·연도·URL이 불확실하면 비워 두고 `verify_status: needs_check`로 둡니다.
  서버는 이 표시를 사용자에게 그대로 보여 줍니다. 빈칸이 지어낸 값보다 낫습니다.
- `stance`는 **그 출처가 새마을운동을 어떻게 평가하는지**이지, 넣는 사람의 생각이 아닙니다.
- 비판 출처를 뺀 채로 지지 출처만 늘리지 마십시오. `saemaul_compare_stances`가 한쪽만 보여 주게 됩니다.
- 근거로 쓰지 않기로 한 자료는 지우지 말고 `excluded:`에 **이유와 날짜를 적어** 옮깁니다.

## 2. 원문 문서 더하기

문서 하나는 세 파일로 이뤄집니다. 앞의 둘을 만들면 셋째는 스크립트가 만듭니다.

### (1) 판독문 — `data/documents/<DOC-ID>.transcript.txt`

```
[문서 제목]
1972.4.26. (광주)

1. 첫 장 제목
(1) 첫 항입니다. 한 단락은 한 줄로 씁니다.
(2) 다음 항입니다.
 - 앞 항에 딸린 열거는 하이픈으로 시작합니다.

2. 다음 장 제목
가. 절 제목
(1) 절 안의 항입니다.

---
[참고 어휘 설명]
(*) 낱말: 뜻풀이
```

- **한 단락 = 한 줄.** 줄을 나누면 다른 단락이 됩니다.
- 한자는 `근면(勤勉)`처럼 괄호로 병기합니다. 그러면 한글로도 한자로도 검색됩니다.
- 장 번호가 원문에서 뒤섞여 있어도 원문 그대로 둡니다. 인용 표기는 원문 번호를 따릅니다.

### (2) 서지 메타 — `data/documents/<DOC-ID>.meta.yaml`

`DOC-1972-0426.meta.yaml`을 복사해 고치는 것이 가장 빠릅니다. 꼭 채워야 하는 것들입니다.

| 필드 | 왜 필요한가 |
|---|---|
| `title`, `author`, `date`, `holder` | 인용 표기를 만드는 데 쓰입니다 |
| `significance` | 에이전트가 이 문서를 왜 봐야 하는지 판단합니다 |
| `archival_reference` | 소장 기관의 관리번호. 모르면 `null` + `needs_check` |
| `transcription.verify_status` | 원본과 대조했는지 |
| `rights.status` | 재배포해도 되는지. **확인 전이면 `needs_check`** |
| `topics` | 검색에 걸릴 주제 태그 |

### (3) 생성

```bash
python3 scripts/build_document.py data/documents/<DOC-ID>.transcript.txt
```

`<DOC-ID>.yaml`이 만들어집니다. 이 파일은 손으로 고치지 않습니다. 커밋에는 함께 넣습니다.

### 스캔 원본

`data/scans/<DOC-ID>.pdf`에 둡니다. 큰 파일이면 Git LFS를 쓰십시오.

```bash
git lfs install && git lfs track "data/scans/*.pdf"
```

**재배포 권리를 확인하지 않은 스캔은 올리지 마십시오.** [NOTICE.md](NOTICE.md)를 먼저 읽으십시오.
스캔 없이 판독문과 서지만 있어도 서버는 그대로 동작합니다.

## 3. 교차참조 — 원문과 연구를 잇기

이 저장소에서 가장 값이 나가는 부분입니다. 원문의 한 대목이 **어떤 논쟁의 근거가 되는지**를 적습니다.
`meta.yaml`의 `cross_references`에 씁니다.

```yaml
cross_references:
  - passage: p065                       # 생성된 .yaml 에서 단락 id를 확인합니다
    note: "'위에서 강요해서 하는 것은 성공 못 한다'. 자발성 주장과 강제성 비판이 부딪히는 대목."
    links:
      - {source: SRC-SCH-002, relation: contested_by}
      - {source: SRC-SCH-004, relation: interprets}
```

| `relation` | 뜻 |
|---|---|
| `interprets` | 이 대목을 해석할 틀을 주는 이론·연구 |
| `contested_by` | 이 대목의 주장을 반박하거나 문제 삼는 연구 |
| `corroborates` | 같은 사실을 다른 기록으로 뒷받침 |

한 단락에 `contested_by`만, 또는 `interprets`만 달리지 않게 살펴 주십시오.
논쟁이 있는 대목이라면 양쪽을 다 다는 것이 이 저장소의 방식입니다.

## 4. 검색어 사전

사람이 쓰는 말로 찾았는데 안 걸리면 `data/search_aliases.yaml`에 한 줄 추가합니다.

```yaml
  마을: [부락, 동리, 部落, 洞里, village]
```

**같은 것을 가리키는 다른 말**만 넣습니다. 연관어를 넣으면 엉뚱한 결과가 섞입니다.
짧은 낱말(두 글자)은 우연히 걸릴 수 있으니 넣기 전에 `--search`로 확인하십시오.

```bash
python3 saemaul_mcp_server.py --search "마을"
```

## 5. 판독 오류를 고칠 때

`transcript.txt`를 고치고 다시 생성하면 됩니다. 다만 **단락 id(p001…)는 줄 순서로 매겨지므로**,
줄을 더하거나 빼면 그 뒤의 id가 밀립니다. 그러면 `cross_references`의 `passage`도 함께 고쳐야 합니다.
생성 후 반드시 확인하십시오.

```bash
python3 tests/smoke_test.py
```

낱말 몇 개만 고치는 교정이라면 줄 수가 그대로이므로 id도 그대로입니다.

---

## 이 저장소가 지키는 것

- 지어내지 않습니다. 모르면 비우고 `needs_check`로 둡니다.
- 뺀 것은 이유와 함께 남깁니다. 조용히 지우지 않습니다.
- 1차 기록은 의도를 보여 줄 뿐 결과를 입증하지 않는다는 구분을 흐리지 않습니다.
- 비판 연구를 같이 싣습니다. 한쪽만 모은 목록은 받지 않습니다.

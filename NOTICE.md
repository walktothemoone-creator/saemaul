# 자료 출처와 권리 / Materials and rights

코드는 MIT입니다([LICENSE](LICENSE)). 자료는 종류마다 권리가 다릅니다. 이 문서가 그 구분입니다.

## 이 저장소가 만든 것

| 대상 | 내용 | 권리 |
|---|---|---|
| `data/sources.yaml` | 출처를 고르고 분류하고 설명을 붙인 편집물 | 기여자들의 편집 저작물. 출처를 밝히고 쓰십시오. |
| `data/documents/*.meta.yaml` | 서지 메타와 교차참조 | 위와 같음 |
| `data/search_aliases.yaml` | 검색어 사전 | 위와 같음 |

레지스트리에 적힌 **서지 사실 자체**(제목·저자·연도·URL)는 사실 정보이며 누구의 것도 아닙니다.
다만 무엇을 넣고 뺐는지, 어떤 관점으로 분류했는지는 이 저장소의 편집 판단입니다.

## 다른 데서 온 것

### `data/scans/DOC-1972-0426.pdf` — 친필 구상 메모 스캔

- 소장: 국가기록원. 국가기록원 원문뷰어 출력본입니다.
- 작성: 박정희, 1972년 4월 26일, 대통령비서실 용지.
- **권리 상태: 확인 전(`needs_check`)**

공공기록물이라고 해서 자동으로 자유 이용이 되지는 않습니다. 이 저장소를 공개로 올리기 전에
다음을 확인하시기 바랍니다.

1. 국가기록원에서 이 기록물의 **관리번호**와 **공개 구분**을 확인합니다.
2. 해당 기록물의 **복제·재배포 조건**을 확인합니다. (공공누리 유형 표시가 있으면 그 유형을 따릅니다.)
3. 확인 결과를 `data/documents/DOC-1972-0426.meta.yaml`의 `archival_reference`와 `rights`에 적습니다.

재배포가 허용되지 않는 것으로 확인되면, 스캔 파일은 저장소에서 빼고 판독문과 서지만 남기면 됩니다.
서버는 스캔 파일이 없어도 그대로 동작합니다. 그때는 `meta.yaml`의 `scan`을 비우고
`archival_reference.url`에 국가기록원 열람 주소를 넣으십시오.

MCP 서버는 이 권리 상태를 숨기지 않습니다. `saemaul_editorial_notes`와
`saemaul_get_document`가 `rights.status`를 그대로 돌려줍니다.

### `data/documents/DOC-1972-0426.transcript.txt` — 판독문

저장소 기여자가 친필을 읽어 옮긴 것입니다. 한자를 괄호로 병기했고, 어려운 낱말 풀이를 붙였습니다.
**원본과 한 줄씩 대조한 교정 기록이 아직 없습니다.** 인용할 때는 스캔 원본을 함께 확인하십시오.
판독에서 생긴 오류를 발견하시면 고쳐 주십시오([CONTRIBUTING.md](CONTRIBUTING.md)).

## 편집 판단을 밝힙니다

이 저장소는 중립을 표방하지 않고, **편집 판단을 기록으로 남기는 쪽**을 택했습니다.
`data/sources.yaml`의 `excluded` 항목에 무엇을 왜 뺐는지 적혀 있고,
`saemaul_editorial_notes` 도구가 그 목록과 이유를 그대로 돌려줍니다.

쓰시는 분들께 당부드립니다.

- 1차 기록은 **무엇을 의도했는지**를 보여 줍니다. 그 의도가 실제로 어떻게 집행되었고
  어떤 결과를 낳았는지는 다른 자료로 따져야 합니다. 서버의 설명문에도 같은 내용이 들어 있습니다.
- 새마을운동은 평가가 갈리는 주제입니다. 이 저장소는 비판 연구를 함께 싣고
  `saemaul_compare_stances`로 같이 보도록 만들었습니다. 한쪽만 인용하지 마십시오.

---

# English summary

Code is MIT. Materials are not.

- `data/sources.yaml`, `*.meta.yaml`, `search_aliases.yaml` are editorial compilations by this
  repository's contributors. Attribution requested.
- `data/scans/DOC-1972-0426.pdf` is a scan of a public record held by the **National Archives of
  Korea** (handwritten note by Park Chung-hee, 26 April 1972). **Its redistribution status has not
  been verified** — see the Korean section above before publishing this repository. The server
  reports this status through `saemaul_editorial_notes` rather than hiding it.
- The transcript is a contributor's reading of the manuscript and has **not** been collated
  line-by-line against the scan.

Saemaul Undong is a contested subject. This repository carries critical scholarship alongside
primary records and exposes its own exclusions. Primary records show intent, not outcomes.

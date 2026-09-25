# 진행 상황 (2026-09-25 갱신, 다섯 번째)

## 목표

회의 녹음 파일 하나를 넣으면 사람 개입 없이 회의록 정리본이 노션에 올라가는 명령줄 Python 스크립트 (`docs/spec.md`, v0.6).
**5단계 전부 완성, 명세서 완료 기준 충족.** 실제 녹음 2개(2분, 50분)로 `run.py` 한 번에 노션 페이지가 생기는 것을 실행 확인했다. 이후는 폴더 정리와 실험(키워드 부스팅)을 했고, 남은 건 사용자가 노션 결과를 검토하며 지적하는 품질 개선.
`docs/spec.md`는 사용자가 브레인스토밍한 것을 AI가 받아 적은 문서라 계속 바뀔 수 있다.

작업 방식: 사용자는 각 스크립트를 코드 레벨이 아니라 흐름(flow) 중심으로 이해하고 넘어가길 원한다. 새 스크립트를 만들면 함수별 역할을 설명하는 시간을 가진 뒤 다음 단계로 간다. 혼자 하는 프로젝트라 PR은 쓰지 않고 `main`에 직접 커밋한다. 커밋·push는 사용자가 시킬 때 한다. 문서에는 사용자가 적으라고 한 내용만 넣고, 제안은 채팅으로 한다. 폴더 구조는 루트 `README.md`의 트리를 참고.

**용어 (`docs/spec.md` "용어" 절)**: 테스트 = 자동 실행·통과/실패(`tests/`). 실험 = 조건을 바꿔 측정·비교·결론, 보고서(`experiments/`). 실행 확인 = 실제 데이터로 한 번 돌려 되는지 봄(`run.py` 실제 녹음). 셋을 "테스트"로 뭉뚱그리지 않는다.

## 완료

- **1단계 `daglo.py`**: 다글로 비동기 STT → `stt_response.json`, `transcript.txt`, `stt_rid.txt`, `recording.json`(녹음 이름·수정 시각, 5단계 회의일). 실행 확인: 50분 녹음(50MB) 36초, 단어 5,095개, 화자 8명.
- **2단계 `transcript.py`**: 화자 전환 기준 발언 → `transcript.md`, `utterances.json`. 실행 확인: 50분 → 발언 341개.
- **3단계 `llm.py`**: Claude `claude-opus-5-5`(`effort="high"`, $4/$20) 1회 호출 → `extraction.json`(`title`, `summary`, `topics`, `decisions[{text,evidence}]`, `todos[{text,evidence,owner,due}]`), `extraction_review.md`, `llm_response.json`. JSON 스키마 강제, `--force` 재호출, 프롬프트 `prompts/extract.md`. 실행 확인: 50분 회의 85초, 입력 29,487·출력 9,124 토큰, $0.30, 요약 4,810자 14문단.
- **4단계 `verify.py`**: `evidence` 번호를 `utterances.json`과 대조, 하나라도 없으면 항목 전체 제외 → `minutes.md`, `verified.json`, `excluded.json`. `evidence_times()` 공개 함수. 실행 확인: 실제 회의 2개 제외 0. 가짜 번호 사본으로 제외 경로 확인.
- **5단계 `notion.py`**: 회의록 DB에 페이지 1개(회의 ID 중복 방지, 제목 `YYYY-MM-DD`/` (n)`, 본문 요약 문단들→대화 주제→결정사항→할 일→제외 목록, 하위 페이지 "원문"에 표 99행씩). API `2025-09-03`, `requests` 직접 호출, `notion_page.json`. 실행 확인: 50분 회의 11초, MCP로 페이지 읽어 속성·본문·표 4개(341행) 확인. 재실행 → "이미 페이지가 있습니다".
- **`run.py`**: 1~5단계 순차 실행, 단계별 시간 출력. 실행 확인: 50분 녹음 처음부터 끝까지 78초, 사람 개입 없음.
- **노션 회의록 DB**: https://app.notion.com/p/4d21d183ff2541f7866cd33220a57883 (개인 공간). 속성: 회의(제목), 회의일, 상태(자동 생성(미검수)/검수 완료), 회의 ID, 녹음 파일, 생성 시각. 데이터 소스 ID `5ed30c30-e1eb-45b8-8604-b645fd57d8b3`. 내부 통합 연결 완료. 사용자가 이전 레코드를 지우고 50분 회의는 새 요약으로 다시 올렸다(페이지 `3e6b855637d9813e8366fd51680fcd43`).
- **폴더 정리** (커밋 `42d39d1`, `251d0a1`): `stt_eval/` → `experiments/stt_compare/`(평평한 구조), `experiments/keyword_boost/` 추가, `experiments/README.md`(규칙+실험 목록). 파이프라인 테스트 4개 → `tests/`(`__init__.py`로 자동 탐색). 확인: `py -3.12 -m unittest` → 58개 `OK`, `stt_eval` 참조 없음(grep).
- **실험: 다글로 키워드 부스팅** (`experiments/keyword_boost/report.md`, 스크립트 `keyword_boost.py`): 2분 표본 CER 부스팅 없음 10.7%(대조군 재현 동일) / 키워드 2개 boost 1: 12.7% / boost 7: 14.7% / 키워드 9개 boost 7: 15.5%. 켜면 없던 말이 같은 자리에 끼어들고(삽입 11→23→34), 맞던 "구인장"이 "구인자"로 바뀜. **결론: 파이프라인에 넣지 않음.** 실험용으로 만들었던 `daglo.py` 부스팅 코드·`keywords.txt`·`test_daglo.py`는 커밋 없이 되돌렸다(사용자 결정).
- **`docs/spec.md`**: 3단계 Claude·요약, 5단계 결정, 미정 없음, **"용어" 절 추가**(이번 세션, 커밋 대기). 버전 v0.6 유지.
- **테스트 58개 통과** — 확인: 루트에서 `py -3.12 -m unittest` → `OK`. `tests/` 48개(transcript 9, llm 10, verify 13, notion 16) + `experiments/stt_compare/test_cer.py` 10.
- 푸시 상태: `origin/main`은 `e40b994`까지. 로컬은 `251d0a1` + 이번 docs 커밋으로 앞서 있음. **push 안 됨.**

기타 참고:
- 다글로 응답: `sttResults[].words[]` = `{speaker:"1", word:" 네", startTime:{seconds:"0", nanos:...}, ...}`. `seconds`·`speaker` 문자열. `segmentId` 안 씀.
- `runs/`: `2bfc0703de20ad5a`(2분), `6965a6464ec7d562`(50분). 정답 원고 `recordings/21일 점심회의-1-1.정답.txt`(gitignore).
- 노션 휴지통(archived) 페이지는 조회에 안 잡혀 지우고 다시 올릴 수 있다.

## 진행 중

없음. (`docs/spec.md` 용어 절과 이 문서가 커밋 대기 중이면 먼저 커밋.)

## 다음 할 일

1. **push** (로컬이 origin보다 앞섬).
2. **사용자의 노션 페이지 검토** 후 품질 개선. 발견했지만 손대지 않은 것:
   - 요약 문체가 실행마다 다름("~했다"/"~했습니다"). 원하면 `prompts/extract.md`에 문체 한 줄.
   - 회의일은 파일 수정 시각이라 파일을 옮기면 오늘 날짜가 됨. 사용자 결정: 노션에서 직접 고친다.
   - 다글로가 50분 회의에서 화자 8명(화자5~8은 발언 1~6개). 담당자 표기에 영향 없었음.
   - 노션 원문 표가 99행마다 나뉨(API 제한).
3. `daglo.py` 보강(급하지 않음): `stt_rid.txt`만 남고 다글로 작업이 실패하면 재실행 때 실패한 `rid`만 계속 조회. 실패 상태면 `stt_rid.txt` 삭제 또는 재업로드. `experiments/stt_compare/daglo.py` 스냅샷은 건드리지 않는다.
4. 다른 컴퓨터: `README.md` "새 컴퓨터에서 시작할 때". 환경 변수 6개(`DAGLO_API_TOKEN`, `CLOVA_SPEECH_SECRET`, `CLOVA_SPEECH_INVOKE_URL`, `ANTHROPIC_API_KEY`, `NOTION_API_KEY`, `NOTION_DATABASE_ID`) `setx`. `runs/`·`recordings/` gitignore.

## 결정과 이유

- **키워드 부스팅은 쓰지 않는다**: 위 실험. 표본 1개(2분, 소음·끼어들기 많음)라 조용한 녹음은 다를 수 있음. 특정 용어가 계속 틀리면 `experiments/keyword_boost/keyword_boost.py`로 그 단어만 넣어 CER 전후 비교 후 재판단.
- **의미 없다고 결론 난 기능 코드는 커밋하지 않는다**: 사용자가 "부스팅이 의미 없다고 결론 낸 시점에 부스팅 코드를 커밋해야 하나"라고 지적. 되돌리고 실험 기록만 남김.
- **실험은 `experiments/<실험명>/` 하나에 스크립트+보고서를 평평하게**: 사용자 결정. 실험 스크립트는 다른 실험 폴더에 기대지 않게 자체 완결(`keyword_boost.py`가 업로드·폴링 코드를 자체 포함). CER 측정 도구 `cer.py`만 `stt_compare/`에 두고 공용으로 씀. 실험용 `test_cer.py`는 실험 폴더에 둔다.
- **파이프라인 테스트는 `tests/`**: 스프링의 src/test처럼 분리. 사용자 요청. `import llm` 같은 구문은 루트 실행 기준이라 그대로.
- **용어 세 가지(테스트/실험/실행 확인)를 `spec.md`에 명시**: 사용자가 둘을 애매하게 써 왔다고 지적. 영어권 test/experiment(eval)/smoke test 구분에 대응.
- **LLM은 Claude `claude-opus-5-5`** (`ca17c50`): 20% 저렴, 같은 회의 비교에서 더 보수적으로 추출했고 사용자가 더 정확하다고 판단. `effort="high"` 명시(5.5 기본은 medium).
- **요약은 원문 대체용 서술** (`275d2b8`): "3~5문장" 제한 삭제, 흐름 순서·주제별 문단·결정 내용 포함. 비용 $0.19→$0.30.
- **"안건"이 아니라 "대화 주제"(`topics`)**: 안건은 회의 전에 정하는 것. 사용자 지적.
- **4단계는 근거 일부만 가짜여도 항목 전체 제외**: 명세서 규칙, 제외 목록에서 복구 가능.
- **5단계 회의일 = 녹음 수정 시각, 덮어쓰기 없음. 제목 = 회의일(+` (n)`), 회의 ID 속성, 원문은 하위 페이지**: 사용자 결정.
- **노션은 `requests`로 REST 직접 호출**(SDK 안 씀). API `2025-09-03`: 부모 `data_source_id`, 조회 `POST /data_sources/{id}/query`. DB ID만 환경 변수, 데이터 소스 ID는 코드가 조회. rich_text 2,000자·블록 100개·표 99행 분할.
- **터미널 출력에 cp949 밖 문자(`≈`, `—`) 안 씀**. `→`는 가능.
- **테스트는 작게 여러 개**(함수 하나가 규칙 하나). 사용자가 개수를 물어 설명했고 줄이라는 지시 없음.
- **음성 인식은 다글로 유지** (`experiments/stt_compare/decision.md`): CER 10.7% vs 14.4%, 유의미한 차이 아님. 10원/분 vs 28원/분.
- 발언은 화자 전환에서 끊음, `segmentId` 안 씀. 파일 이름: 외부 서비스는 서비스명, 일반 코드는 역할명. 다글로 multipart 직접 업로드·폴링·화자 분리 on·`ko-KR`, 회의 ID = sha256 앞 16자, `rid` 저장.
- API 키는 사용자가 `setx`. 에이전트는 값 출력 안 함. 켜 둔 앱에서는 `[Environment]::GetEnvironmentVariable(이름,'User')`로 불러와 실행.
- `requirements.txt`는 `requests`, `anthropic`, 버전 미고정. `unittest` 사용. `spec.md` v0.6 유지.

## 시도했다가 실패한 것

- **키워드 부스팅** — 위 실험대로 어떤 강도에서도 CER 악화. 코드 되돌림.
- Bash heredoc 안의 `\\n` — 실제 줄바꿈으로 들어가 SyntaxError(이번 세션에 두 번 더, 총 네 번째). 파이썬 문자열 안에 `\n`이 들어가는 코드는 heredoc 대신 Write/Edit 도구로.
- Bash 콘솔은 cp949라 한글 출력이 깨짐 — `PYTHONUTF8=1` 붙이거나 `cat`으로 파일을 읽는다.
- 요약 "3~5문장" 제한 — 50분 회의도 5문장. 제한 제거.
- `test_notion.py` 표 분할 기대값 계산 실수(99행씩이면 `[100,100,53]`).
- `llm.py`의 `≈` — cp949 `UnicodeEncodeError`. `약`으로 교체.
- PowerShell 여러 줄 파이썬은 `Set-Content -Encoding utf8`로 파일에 쓴 뒤 실행.
- 정답 원고 루트 배치 → `recordings/`로 이동, BOM 제거. 첫 CER 43.6%(표 마크업 포함) → 표 인식 추가. 발언별 CER·`segmentId` 발언 단위 폐기. WebFetch로 JS 페이지(다글로 API Reference) 읽기 실패 → OpenAPI yaml `curl`. 노션 개발자 문서는 WebFetch로 읽힘. 앱 "Create PR" 실수 → ff 머지 후 브랜치 삭제.

# 진행 상황 (2026-09-25 갱신, 네 번째)

## 목표

회의 녹음 파일 하나를 넣으면 사람 개입 없이 회의록 정리본이 노션에 올라가는 명령줄 Python 스크립트 (`docs/spec.md`, v0.6).
**5단계 전부 완성.** 실제 녹음 2개(2분, 50분)로 `run.py` 한 번에 노션 페이지가 생기는 것을 확인했다. 명세서 완료 기준 충족. 남은 건 품질 다듬기와 사용자가 지적하는 개선.
`docs/spec.md`는 사용자가 브레인스토밍한 것을 AI가 받아 적은 문서라 계속 바뀔 수 있다.

작업 방식: 사용자는 각 스크립트를 코드 레벨이 아니라 흐름(flow) 중심으로 이해하고 넘어가길 원한다. 새 스크립트를 만들면 함수별 역할을 설명하는 시간을 가진 뒤 다음 단계로 간다. 혼자 하는 프로젝트라 PR은 쓰지 않고 `main`에 직접 커밋한다. 커밋·push는 사용자가 시킬 때 한다. 문서에는 사용자가 적으라고 한 내용만 넣고, 제안은 채팅으로 한다. 폴더 구조는 루트 `README.md`의 트리를 참고.

## 완료

- **1단계 `daglo.py`**: 다글로 비동기 STT multipart 업로드 → 폴링 → `stt_response.json`, `transcript.txt`, `stt_rid.txt`, **`recording.json`(녹음 파일 이름·수정 시각, 5단계가 회의일로 씀. 결과가 있어도 매번 씀)**. 커밋 `264dfdf`, `7cda950`. 확인: 50분 녹음(50MB) 업로드+변환 36초, 단어 5,095개, 화자 8명.
- **2단계 `transcript.py`**: 화자가 바뀌는 지점에서 발언을 끊어 `transcript.md`, `utterances.json`. 커밋 `006ab85`. 확인: 50분 → 발언 341개.
- **3단계 `llm.py`**: `transcript.md`를 Claude **`claude-opus-5-5`**(`output_config.effort="high"` 명시, 단가 $4/$20)에 1회 보내 `extraction.json`(`title`, `summary`, `topics`, `decisions[{text,evidence}]`, `todos[{text,evidence,owner,due}]`), `extraction_review.md`(근거 발언 원문 첨부), `llm_response.json`. 응답 형식은 `output_config` JSON 스키마로 강제. `--force` 재호출. 프롬프트 `prompts/extract.md`. 커밋 `213d24b`, `d956cee`, `ca17c50`, `275d2b8`. 확인: 50분 회의 85초, 입력 29,487·출력 9,124 토큰, $0.30. 요약 4,810자 14문단, 대화 주제 13, 결정사항 7, 할 일 15.
- **4단계 `verify.py`**: 결정사항·할 일의 `evidence`를 `utterances.json`의 `no`와 대조. 번호가 하나라도 없거나 근거가 비면 **항목 전체**를 `excluded.json`으로. 통과분으로 `minutes.md`(근거를 시각으로 표시)와 **`verified.json`**(5단계 입력). `evidence_times()`는 공개 함수로 5단계도 씀. 커밋 `f926aaf`, `7cda950`. 확인: 실제 회의 2개 모두 제외 0. 가짜 번호를 심은 사본으로 제외 경로 동작 확인.
- **5단계 `notion.py`**: 회의록 DB에 페이지 1개. 흐름: DB ID → 데이터 소스 ID(`GET /databases`) → 회의 ID로 기존 페이지 조회(있으면 중단) → 같은 회의일 개수로 제목 결정(`YYYY-MM-DD`, 이미 n개면 `YYYY-MM-DD (n)`) → 본문 블록(요약 문단들 → 대화 주제 → 결정사항 → 할 일 → 제외 목록 → "원문" 안내) → 하위 페이지 "원문"에 발언 표(99행씩 여러 표). `notion_page.json`에 주소 기록. API 버전 `2025-09-03`, `requests` 직접 호출. 커밋 `7cda950`, `275d2b8`. 확인: 50분 회의 11초, 노션 페이지를 MCP로 읽어 속성 6개·본문·표 4개(100·100·100·45행 = 341행) 확인. 같은 회의 ID로 재실행 → "이미 페이지가 있습니다".
- **`run.py`**: 녹음 하나로 1~5단계 순차 실행, 단계별 소요 시간 출력. 확인: 50분 녹음 처음부터 끝까지 78초(요약 개선 전), 사람 개입 없음.
- **노션 회의록 DB**: https://app.notion.com/p/4d21d183ff2541f7866cd33220a57883 (사용자 개인 공간, 세션에서 MCP로 생성). 속성: 회의(제목), 회의일(date), 상태(select: 자동 생성(미검수)/검수 완료), 회의 ID(text), 녹음 파일(text), 생성 시각(created_time). 데이터 소스 ID `5ed30c30-e1eb-45b8-8604-b645fd57d8b3`. 스크립트는 내부 통합 토큰(`NOTION_API_KEY`)으로 접근하며 DB에 통합 연결 완료.
- **테스트 58개 전부 통과** — 확인: `py -3.12 -m unittest` → `OK` (cp949 콘솔). transcript 9 + llm 10 + verify 13 + notion 16 + cer 10.
- **문서**: `README.md`(환경 변수 6개, 실행법 1~5단계+run.py, 트리), `docs/spec.md`(3단계 Claude·요약 반영, 5단계 결정 반영, 미정 항목 없음, 버전 v0.6 유지).
- 모든 커밋 `origin/main`에 푸시됨. 확인: `git status -sb` → `## main...origin/main`, 작업 트리 깨끗함. 마지막 커밋 `275d2b8`.

기타 참고:
- 다글로 응답 구조: `sttResults[].words[]` = `{speaker:"1", word:" 네", startTime:{seconds:"0", nanos:...}, endTime, segmentId}`. `seconds`·`speaker`는 문자열. `segmentId` 안 씀.
- `runs/` 안 회의: `2bfc0703de20ad5a`(2분, `recordings/21일 점심회의-1-1.m4a`), `6965a6464ec7d562`(50분, `recordings/21일 점심회의.m4a`). 둘 다 노션에 페이지 있음(사용자가 이전 레코드를 지우고 50분 것은 새 요약으로 다시 올림).

## 진행 중

없음.

## 다음 할 일

1. **사용자가 노션 페이지 검토** 후 지적하는 품질 개선. 이번 세션에서 발견했지만 아직 손대지 않은 것:
   - 요약 문체가 실행마다 다름("~했다" / "~했습니다"). 원하면 `prompts/extract.md`에 문체 한 줄 추가.
   - 회의일은 파일 수정 시각이라 파일을 옮기면 오늘 날짜가 됨(50분 회의가 25일로 들어감). 사용자 결정: 노션에서 직접 고친다. 코드 변경 없음.
   - 다글로가 50분 회의에서 화자 8명을 잡았는데 화자5~8은 발언 1~6개(잡음·끼어들기로 추정). 정리본 담당자에는 영향 없었음.
   - 노션 원문 표가 99행마다 끊겨 여러 표가 됨(API 제한). 사용자 불만 없으면 그대로.
2. `daglo.py` 보강(사용자가 주석으로 지적, 급하지 않음): `stt_rid.txt`만 남고 다글로 작업이 실패하면 재실행 때 실패한 `rid`만 계속 조회. 실패 상태를 받으면 `stt_rid.txt`를 지우거나 재업로드. `stt_eval/scripts/daglo.py` 스냅샷은 건드리지 않는다.
3. 다른 컴퓨터에서 작업할 때: `README.md` "새 컴퓨터에서 시작할 때". 환경 변수 6개(`DAGLO_API_TOKEN`, `CLOVA_SPEECH_SECRET`, `CLOVA_SPEECH_INVOKE_URL`, `ANTHROPIC_API_KEY`, `NOTION_API_KEY`, `NOTION_DATABASE_ID`)는 컴퓨터마다 `setx`. `runs/`·`recordings/`는 gitignore.

## 결정과 이유

- **LLM은 Claude `claude-opus-5-5`** (Opus 5에서 변경, `ca17c50`). 입력 $4·출력 $20으로 20% 저렴. 같은 회의로 비교하니 5.5가 더 보수적으로 추출(결정 2→1, 할 일 4→2)했고 사용자가 5.5 쪽이 더 정확하다고 판단. Opus 5.5는 기본 effort가 `medium`이라 `high`를 명시. thinking 비활성화·강제 tool_choice·컴퓨터 사용은 안 써서 호환성 문제 없음.
- **요약은 원문 대체용 서술** (`275d2b8`). 처음엔 "3~5문장"으로 제한했더니 50분 회의도 5문장. 사용자 요구: 원문을 안 읽어도 회의 내용을 빠짐없이 알 수 있는 요약. 길이 제한을 없애고 흐름 순서·주제별 문단·결정 내용 포함으로 규칙 변경. 비용은 $0.19→$0.30.
- **"안건"이 아니라 "대화 주제"(`topics`)**: 안건은 회의 전에 정하는 것이라 STT에서 뽑는 건 실제 오간 주제. 사용자 지적.
- **4단계는 근거 번호 일부만 가짜여도 항목 전체 제외**: 명세서 규칙 그대로, 제외 목록에 원래 항목이 남아 복구 가능.
- **5단계 회의일 = 녹음 파일 수정 시각, 명령줄 덮어쓰기 없음**: 사용자 결정. 틀리면 노션에서 직접 고친다.
- **레코드 제목 = 회의일, 같은 날 n번째면 " (n)"**. 회의 ID는 속성. 본문에 정리본, 맨 아래 하위 페이지 "원문"에 표: 사용자 결정. 휴지통(archived) 페이지는 조회에 안 잡혀 지우고 다시 올릴 수 있음.
- **노션은 `requests`로 REST 직접 호출**, SDK 안 씀(`daglo.py`와 같은 방식, 의존성 최소). API 버전 `2025-09-03`: 페이지 부모는 `data_source_id`, 조회는 `POST /data_sources/{id}/query`. DB ID만 환경 변수로 받고 데이터 소스 ID는 코드가 조회.
- **노션 텍스트 제한 대응**: rich_text 2,000자씩 조각, 요청당 블록 100개씩 분할, 표는 행 99개+머리글로 나눠 여러 표.
- **터미널 출력에 cp949 밖 문자(`≈`, `—`) 쓰지 않음**: 한국어 Windows 콘솔에서 `UnicodeEncodeError`. `→`는 cp949에 있어 괜찮음.
- **테스트는 작게 여러 개**: 함수 하나가 한 규칙만 확인. 사용자가 "왜 이렇게 많냐"고 물어 설명했고 줄이라는 지시는 없었음.
- **음성 인식은 다글로 유지** (`stt_eval/docs/decision.md`). CER 10.7% vs CLOVA 14.4%, 표본 1개라 유의미한 차이 아님. 비용 10원/분 vs 28원/분.
- **`stt_eval/`는 실험 당시 스크립트 보존**, 루트 코드가 바뀌어도 안 고침. `__init__.py`는 unittest 탐색용.
- 발언은 화자가 바뀌는 지점에서 끊음. `segmentId` 안 씀. 2단계 산출물은 `transcript.md`와 `utterances.json` 둘.
- 파일 이름: 외부 서비스는 서비스명(`daglo.py`, `llm.py`, `notion.py`), 일반 코드는 역할명(`transcript.py`, `verify.py`, `run.py`).
- 다글로: multipart 직접 업로드, 비동기+폴링, 화자 분리 on, `ko-KR`. 회의 ID = 녹음 sha256 앞 16자. `rid` 저장해 재업로드 방지.
- API 키·환경 변수는 사용자가 직접 `setx`. 에이전트는 값을 출력하지 않고 있는지만 확인. `setx` 이전에 켜 둔 앱에서는 `[Environment]::GetEnvironmentVariable(이름,'User')`로 불러와 실행.
- `requirements.txt`는 `requests`, `anthropic`, 버전 미고정. 테스트는 표준 `unittest`.
- `docs/spec.md` 버전 표기는 v0.6 그대로.

## 시도했다가 실패한 것

- 요약 "3~5문장" 제한 — 50분 회의에서도 5문장만 나옴. 길이 제한 제거로 해결.
- `test_notion.py` 표 분할 기대값 `[100,100,54]` — 250행을 99개씩 나누면 99+99+52라 `[100,100,53]`이 맞음. 계산 실수.
- `llm.py`의 `≈` — cp949 콘솔 `UnicodeEncodeError`. `약`으로 교체(`d645285`).
- Bash로 파이썬 출력을 볼 때 한글이 깨짐 — 도구 콘솔이 cp949. `PYTHONUTF8=1`을 붙이면 됨. 파일 내용 확인은 `cat`이 안전.
- Bash heredoc 안의 `\\n` — 실제 줄바꿈으로 들어가 SyntaxError(세 번째 겪음). 이스케이프가 있는 코드는 Write/Edit 도구로.
- PowerShell에서 여러 줄 파이썬은 `Set-Content -Encoding utf8`로 파일에 쓴 뒤 실행.
- 정답 원고가 루트에 놓여 git 추적됨 → `recordings/`로 이동. BOM 제거.
- 첫 CER 43.6% — 표 마크업까지 셈. 표 인식 추가 후 10.7%.
- 발언별 CER, `segmentId` 발언 단위 — 폐기.
- WebFetch로 JS 렌더링 페이지 읽기 — 제목만 나옴. OpenAPI yaml을 `curl`로 받는 게 빠름. 노션 개발자 문서는 WebFetch로 잘 읽힘.
- 앱 "Create PR" 버튼 실수 — `main`에 ff 머지 후 브랜치 삭제.

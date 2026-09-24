# 진행 상황 (2026-09-25 갱신, 두 번째)

## 목표

회의 녹음 파일 하나를 넣으면 사람 개입 없이 회의록 정리본이 노션에 올라가는 명령줄 Python 스크립트 (`docs/spec.md`, v0.6).
5단계 중 1단계(다글로 음성 인식)와 2단계(원문 만들기)가 끝났고 실제 녹음으로 확인했다. 음성 인식 서비스는 비교 실험 끝에 다글로로 확정했다. 다음은 3단계(LLM 추출)이며 시작 전에 LLM 제공자·모델을 정해야 한다.
`docs/spec.md`는 사용자가 브레인스토밍한 것을 AI가 받아 적은 문서라 계속 바뀔 수 있다.

작업 방식: 사용자는 각 스크립트를 코드 레벨이 아니라 흐름(flow) 중심으로 이해하고 넘어가길 원한다. 새 스크립트를 만들면 함수별 역할을 설명하는 시간을 가진 뒤 다음 단계로 간다. 혼자 하는 프로젝트라 PR은 쓰지 않고 `main`에 직접 커밋한다. 문서에는 사용자가 적으라고 한 내용만 넣고, 제안은 채팅으로 한다. 폴더 구조는 루트 `README.md`의 트리를 참고.

## 완료

- **1단계 `daglo.py`**: 다글로 비동기 STT에 multipart 직접 업로드 → 폴링 → `runs/<회의ID>/stt_response.json`, `transcript.txt`, `stt_rid.txt`. 커밋 `264dfdf`(+주석 `ab9ae14`, `b271e04`). 확인: 실제 녹음(`recordings/21일 점심회의-1-1.m4a`, 2분)으로 11초 만에 변환, 화자 4명.
- **2단계 `transcript.py`**: 단어 목록을 화자가 바뀌는 지점에서 끊어 `transcript.md`(`| 번호 | 시각 | 화자 | 내용 |`)와 `utterances.json` 저장. 커밋 `006ab85`. 확인: 실제 응답으로 `단어 210개 → 발언 23개`.
- **테스트 19개 전부 통과** — 확인: 루트에서 `py -3.12 -m unittest -v` → `OK`. 2단계 `test_transcript.py` 9개 + CER `stt_eval/tests/test_cer.py` 10개.
- **STT 비교 실험 (`stt_eval/`)**, 커밋 `e6e8c96`:
  - 사용자가 직접 받아쓴 정답 원고(543자, `recordings/21일 점심회의-1-1.정답.txt`, gitignore) 기준 CER: **다글로 10.7%**(치환25/삭제22/삽입11) vs **CLOVA 14.4%**(25/36/17). 확인: `py -3.12 stt_eval/scripts/cer.py <정답> <다글로> <클로바>` 직접 실행.
  - CLOVA 호출 `stt_eval/scripts/clova.py` 실제 실행 성공(동기, 4초, 화자 4명, 세그먼트 23개). 결과 `runs/2bfc0703de20ad5a/clova_response.json`, `clova_transcript.txt`.
  - 문서: `stt_eval/docs/results.md`(측정 사실·한계·"유의미한 차이 없음" 결론), `stt_eval/docs/decision.md`(다글로 유지 결정·근거·비용 비교).
- **루트 `README.md`**: 새 컴퓨터 설정(환경 변수 표에 CLOVA 2개 추가), 실행법, 폴더 구조 트리와 파일별 한 줄 역할. 커밋 `6216c94`.
- 모든 커밋이 `origin/main`(https://github.com/yyy5044/seogi.git)에 푸시됨. 확인: `git status -sb` → `## main...origin/main`, 작업 트리 깨끗함.

다글로 응답 구조 (뒤 단계에서 참고): `sttResults[].words[]` 항목 = `{speaker:"1", word:" 네", startTime:{seconds:"0", nanos:830000000}, endTime, segmentId}`. `seconds`·`speaker`·`segmentId`는 문자열, `nanos`만 정수. 단어 앞에 공백. `segmentId`는 쓰지 않는다.

## 진행 중

없음. 3단계 이후는 시작하지 않았다.

## 다음 할 일

1. **LLM 제공자와 모델 결정** (명세서 미정 항목) — 3단계 코드를 쓰기 전에 필요. 사용자에게 질문. 결정되면 API 키 환경 변수 이름을 정해 `README.md` 환경 변수 표에 한 줄 추가, `requirements.txt`에 라이브러리 추가. (Anthropic/Claude를 쓰게 되면 `claude-api` 스킬을 먼저 읽는다.)
2. **3단계 LLM 추출** — 입력 `runs/<회의ID>/transcript.md`(또는 `utterances.json`), 출력 `runs/<회의ID>/extraction.json`(제목·안건·결정사항·할 일). 결정사항과 할 일에는 근거 발언 번호(`no`)를 함께 적게 한다. LLM 호출 1회. 외부 서비스 파일 규칙에 따라 `llm.py` 같은 파일 하나. 작성 후 사용자에게 함수별 흐름 설명. 완성되면 루트 `README.md` 트리에 추가.
3. **4단계 근거 검증** — `extraction.json`의 근거 번호가 `utterances.json`에 실제로 있는지 코드로 확인. 없으면 정리본에서 빼고 제외 목록에 남긴다. 정리본에는 근거를 해당 발언의 시각으로 표시. 자동 테스트(가짜 근거 번호 항목이 제외된다 / 정상 항목은 통과한다)는 명세서 완료 기준.
4. 5단계 전에 남은 미정 2개 질문: 회의 날짜 출처 / 노션 회의록 DB 구성과 원문 위치(본문·토글·하위 페이지).
5. `daglo.py` 보강(사용자가 주석으로 지적): `stt_rid.txt`만 남고 다글로 쪽 작업이 실패하면 재실행 때 계속 실패한 `rid`만 조회한다. 실패 상태를 받으면 `stt_rid.txt`를 지우거나 재업로드하도록 고친다. 급하지 않음. 고치더라도 `stt_eval/scripts/daglo.py` 스냅샷은 건드리지 않는다.
6. 다른 컴퓨터에서 작업할 때: `README.md`의 "새 컴퓨터에서 시작할 때" 참고. 환경 변수(`DAGLO_API_TOKEN`, `CLOVA_SPEECH_SECRET`, `CLOVA_SPEECH_INVOKE_URL`)는 컴퓨터마다 `setx`로 다시 설정. `runs/`·`recordings/`는 gitignore라 그 컴퓨터에는 없다.

## 결정과 이유

- **음성 인식은 다글로 유지** (`stt_eval/docs/decision.md`). 2분·소음·끼어들기 많은 표본 1개, 정답이 다글로 결과 기반이라 10.7% vs 14.4%는 유의미한 차이가 아님. 비용은 화자 분리 포함 다글로 10원/분(정가 20원, 할인 기간 미확인) vs CLOVA 28원/분(인식 20 + 화자 분리 8). 다글로는 화자 분리 기본·별도 저장소 불필요, 1·2단계 코드가 이미 다글로 기준으로 검증됨. 다글로 모델은 `general` 하나만 선택 가능(OpenAPI 명세 확인). CLOVA Free/Basic은 과금만 다르고 모델 차이 문서에 없음.
- **`stt_eval/`는 실험 당시 스크립트를 그대로 보존**하는 폴더. 루트 `daglo.py`가 바뀌어도 `stt_eval/scripts/daglo.py` 복사본은 고치지 않는다. 동작하지 않아도 무관, "무엇으로 측정했는가"의 기록이 목적 — 사용자 결정. 구성은 `scripts/`(인식·측정), `tests/`, `docs/`. `__init__.py`는 unittest 자동 탐색과 `from stt_eval.scripts.cer import` 경로 때문에 필요.
- 실험 결과(`results.md`)와 결정(`decision.md`)은 문서를 분리 — 사용자 요청. 결과에는 측정한 사실만.
- CER은 공백·문장 부호를 지우고 비교. 표 형식 입력이면 내용 열만 뽑아 비교(정답 원고가 `transcript.md` 형식으로 작성됐기 때문). 발언별 CER은 두 서비스의 발언 경계가 달라 무의미해서 전체 CER만 사용.
- 발언은 화자가 바뀌는 지점에서 끊는다. `segmentId`는 다글로 OpenAPI 스키마에 정의가 없고(가이드 예제에만 등장), 실제 데이터에서 평균 2.6단어짜리 인식 구간이라 쓰지 않는다. 짧은 맞장구도 발언 하나로 남긴다.
- 2단계 산출물은 `transcript.md`(LLM 입력·노션용 표)와 `utterances.json`(4단계 대조용) 둘.
- 테스트는 표준 라이브러리 `unittest`, 표본은 지어낸 단어(원문은 저장소에 올리지 않음). `requirements.txt`는 `requests` 하나, 버전 미고정.
- 파일 이름: 외부 서비스는 서비스명(`daglo.py`, 나중에 `notion.py`, `llm.py`), 일반 코드 단계는 역할명(`transcript.py`).
- 다글로: multipart 직접 업로드(S3·URL 안 씀), 비동기+폴링, 화자 분리 on, `ko-KR`, `speakerCountHint` 없음. 회의 ID = 녹음 sha256 앞 16자. 업로드 직후 `rid` 저장해 재업로드(과금) 방지.
- API 키는 사용자가 직접 `setx`. 에이전트는 값을 입력·출력하지 않고 있는지만 확인한다. `setx` 이전에 켜 둔 앱에서는 `[Environment]::GetEnvironmentVariable(이름,'User')`로 불러와 실행.
- PR 미사용, `main` 직접 커밋. `gh` CLI는 설치되어 있으나 로그인 안 됨.
- `docs/spec.md` 버전 표기는 v0.6 그대로.

## 시도했다가 실패한 것

- 정답 원고가 루트 `회의록 정답.txt`에 놓여 git 추적 대상으로 잡힘 → `recordings/`로 옮김(gitignore). 메모장 UTF-8 BOM이라 BOM 없는 UTF-8로 재저장.
- 첫 CER 계산 43.6% — 정답이 표 형식이라 번호·시각·화자 마크업까지 글자로 셈. `cer.py`에 표 인식(`extract_text`) 추가 후 10.7%.
- 발언별 CER 비교 — CLOVA 세그먼트 경계가 정답 행과 달라 순서대로 짝지으면 엉뚱한 문장끼리 비교됨. 폐기.
- `segmentId`를 발언 단위로 쓰려던 계획 — 문서 정의 없음, 단위가 너무 작음. 폐기.
- WebFetch로 JS 렌더링 페이지(다글로 API Reference, 네이버 클라우드 요금 페이지) 읽기 — 제목만 나옴. 내장 브라우저에서 JS로 shadow DOM 텍스트를 모으거나, 페이지가 불러오는 OpenAPI yaml(`https://apis.daglo.ai/en/openapi.prod.en.yaml`)을 `curl`로 받는 게 빠르다.
- Bash heredoc으로 파이썬 파일을 쓸 때 `\\`가 `\`로 들어가 SyntaxWarning/SyntaxError — 두 번 겪음. 이스케이프가 있는 코드는 heredoc 대신 Write/Edit 도구로.
- 앱의 "Create PR" 버튼을 실수로 눌러 브랜치가 생김 — `main`에 ff 머지 후 브랜치 삭제.
- PowerShell에서 `py -c @'...'@` 여러 줄 파이썬 — 큰따옴표가 사라져 SyntaxError. 파일로 저장해 실행.

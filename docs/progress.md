# 진행 상황 (2026-09-25 갱신, 세 번째)

## 목표

회의 녹음 파일 하나를 넣으면 사람 개입 없이 회의록 정리본이 노션에 올라가는 명령줄 Python 스크립트 (`docs/spec.md`, v0.6).
5단계 중 1단계(다글로 음성 인식)·2단계(원문 만들기)·3단계(Claude 추출)가 끝났고 실제 녹음으로 확인했다. 다음은 4단계(근거 검증)이다.
`docs/spec.md`는 사용자가 브레인스토밍한 것을 AI가 받아 적은 문서라 계속 바뀔 수 있다.

작업 방식: 사용자는 각 스크립트를 코드 레벨이 아니라 흐름(flow) 중심으로 이해하고 넘어가길 원한다. 새 스크립트를 만들면 함수별 역할을 설명하는 시간을 가진 뒤 다음 단계로 간다. 혼자 하는 프로젝트라 PR은 쓰지 않고 `main`에 직접 커밋한다. 문서에는 사용자가 적으라고 한 내용만 넣고, 제안은 채팅으로 한다. 폴더 구조는 루트 `README.md`의 트리를 참고.

## 완료

- **1단계 `daglo.py`**: 다글로 비동기 STT에 multipart 직접 업로드 → 폴링 → `runs/<회의ID>/stt_response.json`, `transcript.txt`, `stt_rid.txt`. 커밋 `264dfdf`(+주석 `ab9ae14`, `b271e04`). 확인: 실제 녹음(`recordings/21일 점심회의-1-1.m4a`, 2분)으로 11초 만에 변환, 화자 4명.
- **2단계 `transcript.py`**: 단어 목록을 화자가 바뀌는 지점에서 끊어 `transcript.md`(`| 번호 | 시각 | 화자 | 내용 |`)와 `utterances.json` 저장. 커밋 `006ab85`. 확인: 실제 응답으로 `단어 210개 → 발언 23개`.
- **3단계 `llm.py`**: `transcript.md`를 Claude(`claude-opus-5`)에 1회 보내 `extraction.json`(제목·안건·결정사항·할 일, 결정사항과 할 일에 근거 발언 번호 `evidence`), `extraction_review.md`(근거 번호 옆에 실제 발언을 붙인 검토용), `llm_response.json`(응답 원본·토큰 사용량) 저장. 응답 형식은 `output_config` JSON 스키마(`SCHEMA`)로 API 수준에서 강제. `--force`로 재호출. 시스템 프롬프트는 `prompts/extract.md` 파일로 분리. 커밋 `213d24b`, `d645285`(비용 출력의 `≈`를 `약`으로 — cp949 콘솔에서 `UnicodeEncodeError`).
  확인: 실제 회의(`runs/2bfc0703de20ad5a`, 발언 23개)로 호출 성공. 모델 `claude-opus-5`, `stop_reason=end_turn`, 입력 3130 토큰·출력 1118 토큰(그중 thinking 573). 결과: 안건 5개, 결정사항 2개, 할 일 5개, 근거 번호는 전부 1~15 범위(원문 안). 결과 문장의 품질은 사용자가 아직 검토하지 않음(미확인).
- **테스트 29개 전부 통과** — 확인: 루트에서 `py -3.12 -m unittest` → `OK` (기본 cp949 콘솔, `PYTHONUTF8` 없이). 2단계 `test_transcript.py` 9개 + 3단계 `test_llm.py` 10개(API 호출 없이 파싱·검토 파일·재실행 동작) + CER `stt_eval/tests/test_cer.py` 10개.
- **STT 비교 실험 (`stt_eval/`)**, 커밋 `e6e8c96`: 사용자가 직접 받아쓴 정답 원고(543자, `recordings/21일 점심회의-1-1.정답.txt`, gitignore) 기준 CER 다글로 10.7% vs CLOVA 14.4%. 문서: `stt_eval/docs/results.md`(측정 사실), `stt_eval/docs/decision.md`(다글로 유지 결정).
- **루트 `README.md`**: 환경 변수 표(`DAGLO_API_TOKEN`, `CLOVA_SPEECH_SECRET`, `CLOVA_SPEECH_INVOKE_URL`, `ANTHROPIC_API_KEY`), 실행법(3단계 포함), 폴더 구조 트리(`llm.py`, `test_llm.py`, `prompts/extract.md` 포함). 커밋 `6216c94`, `213d24b`.
- **`docs/spec.md` 갱신**: 단계 표 3단계 성격 칸을 "Claude API 1회 호출 (모델 `claude-opus-5`, JSON 스키마로 응답 형식 강제)"로, 미정 목록에서 "LLM 제공자와 모델" 삭제. 버전 표기는 v0.6 그대로. **아직 커밋 안 됨**(작업 트리에 `M docs/spec.md`).
- 푸시 상태: `origin/main`(https://github.com/yyy5044/seogi.git)은 `213d24b`까지. 로컬 `main`은 `d645285`로 1개 앞섬. 확인: `git status -sb` → `## main...origin/main [ahead 1]`.

다글로 응답 구조 (뒤 단계에서 참고): `sttResults[].words[]` 항목 = `{speaker:"1", word:" 네", startTime:{seconds:"0", nanos:830000000}, endTime, segmentId}`. `seconds`·`speaker`·`segmentId`는 문자열, `nanos`만 정수. 단어 앞에 공백. `segmentId`는 쓰지 않는다.

3단계 산출물 구조 (4단계에서 참고): `extraction.json` = `{title, agenda:[str], decisions:[{text, evidence:[int]}], todos:[{text, evidence:[int], owner, due}]}`. `owner`·`due`는 원문에 없으면 빈 문자열. `evidence`는 `transcript.md`·`utterances.json`의 발언 번호(`no`).

## 진행 중

- `docs/spec.md` 수정분 커밋 대기(위 완료 항목 참고). 이 handoff 문서(`docs/progress.md`) 갱신분도 함께 커밋해야 한다.
- `llm.py` 함수별 흐름 설명을 사용자에게 했는지 미확인(이전 세션 내용). 이번 세션에서는 하지 않았다.

## 다음 할 일

1. `docs/spec.md`·`docs/progress.md` 변경 커밋, 그리고 `git push`(로컬이 origin보다 앞서 있음).
2. 사용자가 `runs/2bfc0703de20ad5a/extraction_review.md`를 눈으로 검토. 결과가 마음에 안 들면 `prompts/extract.md`를 고치고 `py -3.12 llm.py runs/2bfc0703de20ad5a --force`로 재호출(호출마다 과금, 1회 약 $0.04).
3. 필요하면 `llm.py` 함수별 흐름 설명(`load_prompt` → `extract` → `parse_response` → `render_review` → `run`, 비용 계산 `cost_usd`).
4. **4단계 근거 검증** — 입력 `extraction.json` + `utterances.json`, 출력 정리본과 제외 목록. `evidence`의 번호가 `utterances.json`에 실제로 있는지 코드로 확인. 없으면 정리본에서 빼고 제외 목록에 남긴다. 정리본에는 근거를 해당 발언의 시각으로 표시. 일반 코드라 파일 이름은 역할명(예: `verify.py`). 자동 테스트(가짜 근거 번호 항목이 제외된다 / 정상 항목은 통과한다)는 명세서 완료 기준. 작성 후 사용자에게 함수별 흐름 설명, 루트 `README.md` 트리에 추가.
5. 5단계 전에 남은 미정 2개 질문: 회의 날짜 출처 / 노션 회의록 DB 구성과 원문 위치(본문·토글·하위 페이지).
6. `daglo.py` 보강(사용자가 주석으로 지적): `stt_rid.txt`만 남고 다글로 쪽 작업이 실패하면 재실행 때 계속 실패한 `rid`만 조회한다. 실패 상태를 받으면 `stt_rid.txt`를 지우거나 재업로드하도록 고친다. 급하지 않음. 고치더라도 `stt_eval/scripts/daglo.py` 스냅샷은 건드리지 않는다.
7. 다른 컴퓨터에서 작업할 때: `README.md`의 "새 컴퓨터에서 시작할 때" 참고. 환경 변수는 컴퓨터마다 `setx`로 다시 설정. `runs/`·`recordings/`는 gitignore라 그 컴퓨터에는 없다.

## 결정과 이유

- **LLM은 Claude `claude-opus-5`** (이전 세션 결정, 커밋 `213d24b`). 응답 형식은 `output_config` JSON 스키마로 강제해 파싱 실패를 없앰. 근거 번호가 진짜인지는 스키마가 보장하지 못하므로 4단계가 확인한다. 비용 상수 `PRICE_PER_MTOK`는 입력 $5·출력 $25(100만 토큰당)로 코드에 적혀 있음.
- **시스템 프롬프트는 `prompts/extract.md` 파일로 분리** — 결과를 다듬을 때 코드가 아니라 프롬프트 파일만 고치면 되게.
- **검토용 `extraction_review.md`를 따로 만든다** — 근거 번호만 보면 사람이 맞는지 알 수 없어서, 번호 옆에 해당 발언의 시각·화자·내용을 붙인다.
- **터미널 출력에 `≈` 같은 cp949 밖 문자를 쓰지 않는다** — 한국어 Windows 콘솔에서 `UnicodeEncodeError`로 스크립트가 죽는다. 테스트도 같은 이유로 2개 실패했었음.
- **음성 인식은 다글로 유지** (`stt_eval/docs/decision.md`). 표본 1개, 정답이 다글로 결과 기반이라 10.7% vs 14.4%는 유의미한 차이가 아님. 비용 다글로 10원/분 vs CLOVA 28원/분. 다글로 모델은 `general` 하나만 선택 가능.
- **`stt_eval/`는 실험 당시 스크립트를 그대로 보존**. 루트 `daglo.py`가 바뀌어도 `stt_eval/scripts/daglo.py` 복사본은 고치지 않는다 — 사용자 결정. `__init__.py`는 unittest 자동 탐색과 import 경로 때문에 필요.
- CER은 공백·문장 부호를 지우고 비교. 표 형식 입력이면 내용 열만 뽑아 비교. 전체 CER만 사용.
- 발언은 화자가 바뀌는 지점에서 끊는다. `segmentId`는 쓰지 않는다(OpenAPI 스키마에 정의 없음, 평균 2.6단어로 너무 작음). 짧은 맞장구도 발언 하나로 남긴다.
- 2단계 산출물은 `transcript.md`(LLM 입력·노션용 표)와 `utterances.json`(4단계 대조용) 둘.
- 테스트는 표준 라이브러리 `unittest`, 표본은 지어낸 단어. `requirements.txt`는 `requests`, `anthropic`, 버전 미고정.
- 파일 이름: 외부 서비스는 서비스명(`daglo.py`, `llm.py`, 나중에 `notion.py`), 일반 코드 단계는 역할명(`transcript.py`).
- 다글로: multipart 직접 업로드, 비동기+폴링, 화자 분리 on, `ko-KR`, `speakerCountHint` 없음. 회의 ID = 녹음 sha256 앞 16자. 업로드 직후 `rid` 저장해 재업로드(과금) 방지.
- API 키는 사용자가 직접 `setx`. 에이전트는 값을 입력·출력하지 않고 있는지만 확인한다. `setx` 이전에 켜 둔 앱에서는 `[Environment]::GetEnvironmentVariable(이름,'User')`로 불러와 실행.
- PR 미사용, `main` 직접 커밋. `gh` CLI는 설치되어 있으나 로그인 안 됨.
- `docs/spec.md` 버전 표기는 v0.6 그대로(3단계 반영 후에도 유지).

## 시도했다가 실패한 것

- `llm.py` 완료 메시지의 `≈` — cp949 콘솔에서 `UnicodeEncodeError`, 테스트 2개도 같은 이유로 에러. `약`으로 교체(`d645285`). `PYTHONUTF8=1`로도 피할 수 있지만 사용자 터미널 설정에 의존하므로 문자 자체를 바꿈.
- 정답 원고가 루트에 놓여 git 추적 대상으로 잡힘 → `recordings/`로 옮김(gitignore). 메모장 UTF-8 BOM은 BOM 없는 UTF-8로 재저장.
- 첫 CER 계산 43.6% — 정답이 표 형식이라 마크업까지 글자로 셈. `cer.py`에 표 인식 추가 후 10.7%.
- 발언별 CER 비교 — 두 서비스의 발언 경계가 달라 엉뚱한 문장끼리 비교됨. 폐기.
- `segmentId`를 발언 단위로 쓰려던 계획 — 문서 정의 없음, 단위가 너무 작음. 폐기.
- WebFetch로 JS 렌더링 페이지(다글로 API Reference, 네이버 클라우드 요금 페이지) 읽기 — 제목만 나옴. 내장 브라우저에서 JS로 텍스트를 모으거나 OpenAPI yaml(`https://apis.daglo.ai/en/openapi.prod.en.yaml`)을 `curl`로 받는 게 빠르다.
- Bash heredoc으로 파이썬 파일을 쓸 때 `\\`가 `\`로 들어가 SyntaxError — 두 번 겪음. 이스케이프가 있는 코드는 Write/Edit 도구로.
- 앱의 "Create PR" 버튼을 실수로 눌러 브랜치가 생김 — `main`에 ff 머지 후 브랜치 삭제.
- PowerShell에서 `py -c @'...'@` 여러 줄 파이썬 — 큰따옴표가 사라져 SyntaxError. 파일로 저장해 실행.

# 진행 상황 (2026-09-25 갱신, 세 번째)

## 목표

회의 녹음 파일 하나를 넣으면 사람 개입 없이 회의록 정리본이 노션에 올라가는 명령줄 Python 스크립트 (`docs/spec.md`, v0.6).
5단계 중 1단계(다글로 음성 인식)와 2단계(원문 만들기)가 끝났고 실제 녹음으로 확인했다. 3단계(LLM 추출)는 코드와 테스트를 작성해 커밋했지만 **실제 Claude 호출은 아직 해 보지 않았다**. LLM은 Claude Opus 5로 결정했다.
`docs/spec.md`는 사용자가 브레인스토밍한 것을 AI가 받아 적은 문서라 계속 바뀔 수 있다.

작업 방식: 사용자는 각 스크립트를 코드 레벨이 아니라 흐름(flow) 중심으로 이해하고 넘어가길 원한다. 새 스크립트를 만들면 함수별 역할을 설명하는 시간을 가진 뒤 다음 단계로 간다. 혼자 하는 프로젝트라 PR은 쓰지 않고 `main`에 직접 커밋한다. 문서에는 사용자가 적으라고 한 내용만 넣고, 제안은 채팅으로 한다. 폴더 구조는 루트 `README.md`의 트리를 참고.

## 완료

- **1단계 `daglo.py`**: 다글로 비동기 STT에 multipart 직접 업로드 → 폴링 → `runs/<회의ID>/stt_response.json`, `transcript.txt`, `stt_rid.txt`. 커밋 `264dfdf`(+주석 `ab9ae14`, `b271e04`). 확인: 실제 녹음(`recordings/21일 점심회의-1-1.m4a`, 2분)으로 11초 만에 변환, 화자 4명.
- **2단계 `transcript.py`**: 단어 목록을 화자가 바뀌는 지점에서 끊어 `transcript.md`(`| 번호 | 시각 | 화자 | 내용 |`)와 `utterances.json`(`{no, start, speaker, text}`) 저장. 커밋 `006ab85`. 확인: 실제 응답으로 `단어 210개 → 발언 23개`.
- **STT 비교 실험 (`stt_eval/`)**, 커밋 `e6e8c96`: 사용자가 직접 받아쓴 정답 원고 기준 CER 다글로 10.7% vs CLOVA 14.4%. "유의미한 차이 없음" 결론, 다글로 유지. 문서 `stt_eval/docs/results.md`, `decision.md`.
- **테스트 29개 전부 통과** — 확인: 루트에서 `python -m unittest -v` → `OK` (클라우드 세션 Python 3.12에서 실행). 2단계 `test_transcript.py` 9개 + 3단계 `test_llm.py` 10개 + CER `stt_eval/tests/test_cer.py` 10개.
- **3단계 코드 작성** (커밋 `213d24b`, 브랜치 `claude/youthful-allen-ls0lpr`에 푸시됨, `main`에는 아직 안 합침):
  - `llm.py`: `transcript.md`를 `claude-opus-5`에 1회 보내 `extraction.json`(`title`, `agenda[]`, `decisions[{text, evidence[int]}]`, `todos[{text, owner, due, evidence[int]}]`) 저장. 응답 형식은 `output_config={"format": {"type": "json_schema", "schema": SCHEMA}}`로 API가 보장. 함께 `extraction_review.md`(근거 번호 옆에 실제 발언의 시각·화자·내용을 붙인 검토용 파일)와 `llm_response.json`(응답 원본·토큰 사용량) 저장. `extraction.json`이 있으면 호출 안 함, `--force`로 재호출. `stop_reason`이 `refusal`/`max_tokens`면 종료. 소요 시간·항목 수·토큰·달러 비용 출력.
  - `prompts/extract.md`: 시스템 프롬프트 파일. 결과를 다듬을 때 이 파일만 고친다.
  - `test_llm.py`: API 호출 없이 `parse_response`, `render_review`, `cost_usd`, `run`(재실행·`--force`·2단계 결과 없음) 테스트. `mock.patch.object(llm, "extract", ...)`로 호출을 대체.
  - `requirements.txt`에 `anthropic` 추가(클라우드 세션에서 1.8.0 설치해 `messages.create`에 `output_config` 파라미터가 있는 것 확인). README에 `ANTHROPIC_API_KEY` 행, 실행법, 트리 추가.
- 사용자가 `ANTHROPIC_API_KEY`를 자기 컴퓨터에 `setx`로 설정했다고 말함 (에이전트 미확인).

다글로 응답 구조 (뒤 단계에서 참고): `sttResults[].words[]` 항목 = `{speaker:"1", word:" 네", startTime:{seconds:"0", nanos:830000000}, endTime, segmentId}`. `seconds`·`speaker`·`segmentId`는 문자열, `nanos`만 정수. 단어 앞에 공백. `segmentId`는 쓰지 않는다.

## 진행 중

- **3단계 실제 호출 확인 (미실행)**. 클라우드 세션에는 API 키와 `runs/`가 없어 `py -3.12 llm.py runs/<회의ID>`를 실제로 돌려 보지 못했다. 미확인 사항: (1) `SCHEMA`가 API에 받아들여지는지(400이 나면 오류 문구 확인), (2) 실제 회의 원문에서 추출 품질과 근거 번호가 맞는지, (3) 비용·소요 시간. 사용자가 로컬에서 실행한 결과(`extraction_review.md`와 출력 한 줄)를 보고 프롬프트를 다듬는다.
- 브랜치 `claude/youthful-allen-ls0lpr`(커밋 `213d24b`)을 `main`에 ff 머지하는 일이 남아 있다. 사용자 로컬에서: `git fetch origin claude/youthful-allen-ls0lpr && git checkout main && git merge --ff-only origin/claude/youthful-allen-ls0lpr && git push origin main`.

## 다음 할 일

1. **3단계 실제 실행**: 사용자 컴퓨터에서 `py -3.12 -m pip install -r requirements.txt` → `py -3.12 llm.py runs/<회의ID>`. `extraction_review.md`를 같이 보며 결정사항·할 일·근거 번호가 맞는지 눈으로 확인. 문제가 있으면 `prompts/extract.md`를 고치고 `--force`로 재실행. 이 확인이 끝나야 3단계 완료.
2. **4단계 근거 검증** (`verify.py` 같은 역할명 파일): `extraction.json`의 `evidence` 번호가 `utterances.json`의 `no`에 실제로 있는지 코드로 확인. 없는 번호가 하나라도 있는 항목은 정리본에서 빼고 제외 목록에 남긴다(빼는 기준이 "하나라도"인지 "전부"인지는 사용자에게 확인). 정리본에는 근거를 해당 발언의 시각으로 표시. 자동 테스트: 가짜 근거 번호 항목이 제외된다 / 정상 항목은 통과한다 / 빈 입력에서 죽지 않는다. 출력 파일 이름·형식은 5단계(노션) 입력이 되므로 5단계 질문과 같이 정한다.
3. 5단계 전에 남은 미정 2개 질문: 회의 날짜 출처 / 노션 회의록 DB 구성과 원문 위치(본문·토글·하위 페이지).
4. `daglo.py` 보강(급하지 않음): `stt_rid.txt`만 남고 다글로 쪽 작업이 실패하면 재실행 때 계속 실패한 `rid`만 조회한다. 실패 상태를 받으면 `stt_rid.txt`를 지우거나 재업로드하도록 고친다. `stt_eval/scripts/daglo.py` 스냅샷은 건드리지 않는다.
5. 다른 컴퓨터에서 작업할 때: `README.md`의 "새 컴퓨터에서 시작할 때" 참고. 환경 변수(`DAGLO_API_TOKEN`, `CLOVA_SPEECH_SECRET`, `CLOVA_SPEECH_INVOKE_URL`, `ANTHROPIC_API_KEY`)는 컴퓨터마다 `setx`로 다시 설정. `runs/`·`recordings/`는 gitignore라 그 컴퓨터에는 없다.

## 결정과 이유

- **LLM은 Claude Opus 5 (`claude-opus-5`)**. 사용자 결정. 근거: 현재 세대 LLM은 이 작업에 성능이 충분해 제공자 선택에 힘을 들일 이유가 없고, Claude Code와 Anthropic API 참조가 맞물려 개발이 빠르다. 클로드 고유 기능 때문이 아니다(구조화 출력·긴 컨텍스트·추론 조절은 OpenAI·Gemini에도 있음). 다른 제공자와 품질 비교는 하지 않았고, 대신 결과를 눈으로 확인하고 프롬프트를 다듬는 데 시간을 쓴다. `llm.py` 파일 하나에 호출 1회라 교체 비용이 작다. Fable 5.1은 단가 2배·거절 응답 처리·30일 데이터 보존 요건이 있어 제외. 비용 추정: 1시간 회의(입력 약 2.5만 토큰, 출력 3천)에 Opus 5 약 $0.20, Sonnet 5 약 $0.08 (미실측).
- 면접 대비 관점(사용자 우려): "왜 클로드"보다 "LLM 출력을 신뢰하지 않고 4단계에서 근거 번호를 코드로 대조한다"가 진짜 설계 결정. 원하면 `stt_eval/`처럼 `llm_eval/` 비교 실험을 나중에 추가할 수 있다(제안만, 미결정).
- **응답 형식은 JSON 스키마 강제**(`output_config.format`). "JSON으로 답하라"는 프롬프트 지시보다 확실하고, `evidence`를 정수 배열로 고정해 4단계 검증이 단순해진다. 스키마는 형식만 보장하고 번호가 진짜인지는 보장하지 않는다. 어시스턴트 답변 앞부분을 미리 채우는 옛 방식(prefill)은 현재 모델에서 400 오류라 쓰지 않는다. Claude 인용(citations) 기능은 구조화 출력과 같이 쓸 수 없어 이번에는 안 씀(대안으로 기록).
- **프롬프트는 `prompts/extract.md`로 분리**: 다듬는 작업이 텍스트 수정이 되고 커밋 기록으로 남는다. 검토용 `extraction_review.md`를 같이 만들어 원문을 오가지 않고 근거를 확인할 수 있게 했다.
- 추론(thinking)과 `effort`는 기본값(Opus 5는 적응형 추론 기본, effort `high`). 결과를 보고 조절. `temperature`는 Opus 5에서 거부되므로 안 씀. `max_tokens` 16000.
- 안전 분류기 거부 시 다른 모델로 자동 재시도하는 `fallbacks` 옵션은 넣지 않았다. 회의록 추출에서 거부 가능성이 낮고 코드가 복잡해진다. 실제로 거부가 나면 추가.
- `extraction.json`이 있으면 재호출하지 않고 `--force`로만 재호출: 다글로와 같은 멱등성 원칙. 프롬프트 다듬을 때는 `--force`.
- 환경 변수 이름 `ANTHROPIC_API_KEY` (SDK 기본값이라 코드에서 키를 넘길 필요가 없음). API 키 발급: https://console.anthropic.com → Billing에서 선불 크레딧 충전 → API Keys. claude.ai 구독과 별개.
- **음성 인식은 다글로 유지** (`stt_eval/docs/decision.md`). 표본 1개, CER 차이 유의미하지 않음, 비용 다글로 10원/분 vs CLOVA 28원/분, 화자 분리 기본.
- **`stt_eval/`는 실험 당시 스크립트를 그대로 보존**. 루트 `daglo.py`가 바뀌어도 복사본은 고치지 않는다.
- 발언은 화자가 바뀌는 지점에서 끊는다. `segmentId`는 쓰지 않는다. 2단계 산출물은 `transcript.md`(LLM 입력)와 `utterances.json`(4단계 대조용) 둘.
- 테스트는 표준 라이브러리 `unittest`, 표본은 지어낸 내용. 외부 API는 테스트에서 부르지 않는다.
- 파일 이름: 외부 서비스는 서비스명(`daglo.py`, `llm.py`, 나중에 `notion.py`), 일반 코드 단계는 역할명(`transcript.py`).
- 다글로: multipart 직접 업로드, 비동기+폴링, 화자 분리 on, `ko-KR`. 회의 ID = 녹음 sha256 앞 16자. 업로드 직후 `rid` 저장해 재업로드 방지.
- API 키는 사용자가 직접 `setx`. 에이전트는 값을 입력·출력하지 않고 있는지만 확인한다. `setx` 이전에 켜 둔 앱에서는 `[Environment]::GetEnvironmentVariable(이름,'User')`로 불러와 실행.
- PR 미사용, `main` 직접 커밋. 이번 세션은 클라우드 세션이라 지정 브랜치 `claude/youthful-allen-ls0lpr`에 푸시했고 `main` 합치기는 사용자 로컬에서 한다.
- `docs/spec.md` 버전 표기는 v0.6 그대로 (미정 3번 "LLM 제공자와 모델"은 결정됐지만 명세서는 안 고쳤다. 사용자가 적으라고 하면 고친다).

## 시도했다가 실패한 것

- 클라우드 세션에서 `git push` → 403 "Claude doesn't have GitHub access". 사용자가 https://claude.ai/connect-github 에서 GitHub를 다시 연결한 뒤 푸시 성공. 재시도로는 안 풀리는 권한 문제.
- 정답 원고가 루트에 놓여 git 추적 대상으로 잡힘 → `recordings/`로 옮김. 메모장 UTF-8 BOM은 BOM 없는 UTF-8로 재저장.
- 첫 CER 계산 43.6% — 표 마크업까지 셈. `cer.py`에 표 인식 추가 후 10.7%.
- 발언별 CER 비교 — 세그먼트 경계가 달라 무의미. 폐기.
- WebFetch로 JS 렌더링 페이지 읽기 — 제목만 나옴. 내장 브라우저나 OpenAPI yaml(`https://apis.daglo.ai/en/openapi.prod.en.yaml`)을 `curl`로.
- Bash heredoc으로 파이썬 파일을 쓸 때 `\\`가 `\`로 들어가 SyntaxError — 이스케이프가 있는 코드는 Write/Edit 도구로.
- 앱의 "Create PR" 버튼을 실수로 눌러 브랜치가 생김 — `main`에 ff 머지 후 브랜치 삭제.
- PowerShell에서 `py -c @'...'@` 여러 줄 파이썬 — 큰따옴표가 사라져 SyntaxError. 파일로 저장해 실행.

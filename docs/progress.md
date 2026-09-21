# 진행 상황 (2026-09-21 갱신)

## 목표

회의 녹음 파일 하나를 넣으면 사람 개입 없이 회의록 정리본이 노션에 올라가는 명령줄 Python 스크립트 (`docs/spec.md`, v0.6).
지금은 그중 1단계(다글로 API 음성 인식)만 따로 떼어, 녹음 파일을 주고 텍스트/응답을 실제로 받아보는 중이다.
`docs/spec.md`는 사용자가 브레인스토밍한 것을 AI가 받아 적은 문서라 계속 바뀔 수 있다.

## 완료

- 다글로 비동기 STT API가 파일 직접 업로드(multipart/form-data)를 받는다는 것을 확인 — 확인 방법: API Reference(https://apis.daglo.ai/en/docs#/operations/post-stt-v1-async-transcripts) 본문에 명시, Body 탭에 `multipart/form-data`와 `file`(binary, 필수) 필드가 있음. 가이드 문서(developers.daglo.ai/guide)에는 URL 방식 예제만 있다.
- 위 내용을 `docs/spec.md`에 반영 (단계 표 1단계, "단계" 절에 직접 업로드·S3 미사용 항목 추가, 미정 목록에서 1번 삭제) — 미커밋.
- 개발 환경: Python 3.12.10 설치(winget, 사용자가 직접), `requests` 2.34.2 설치 — 확인 방법: `py -3.12 --version`, `py -3.12 -c "import requests"` 실행 성공.
- `.gitignore`에 `.env`, `runs/`, `recordings/`, 녹음 확장자, `.venv/`, `__pycache__/` 추가 — 미커밋.

커밋은 `596349a chore: 초기 설정` 하나뿐이다. 이번 세션 변경(`.gitignore`, `docs/spec.md`, `daglo.py`, `requirements.txt`)은 전부 미커밋이다.

## 진행 중

- `daglo.py` (1단계 음성 인식, 신규 파일): 작성 완료, **API 호출은 한 번도 실행해 보지 못했다.** 문법 검사(`ast.parse`)만 통과.
  - 동작: `py -3.12 daglo.py <녹음 파일>` → multipart로 업로드 → `rid` 수신 → 5초 간격 폴링 → `runs/<파일 sha256 앞 16자>/stt_response.json`(응답 원본), `transcript.txt`(텍스트만) 저장. `rid`는 `stt_rid.txt`에 남겨 재실행 시 재업로드(과금) 없이 조회만 한다.
  - 멈춘 이유: 환경 변수 `DAGLO_API_TOKEN` 미설정, 테스트용 녹음 파일 없음. 토큰은 사용자가 다글로 API 콘솔에서 발급해 직접 설정해야 한다(에이전트는 키를 입력·취급하지 않는다).
  - 미확인 1: `sttConfig`를 multipart 폼 필드에 JSON 문자열로 넣는 방식이 맞는지. 문서에 multipart 예제가 없어 추정으로 작성했다. 첫 실행 후 `stt_response.json`의 `words[]`에 `speaker`가 있는지로 판별한다.
  - 미확인 2: 결과 응답의 실제 구조. 가이드 기준으로는 `{rid, status, sttResults:[{transcript, words:[{word, startTime:{seconds,nanos}, endTime, segmentId, speaker}]}]}`, 완료 상태는 `transcribed`, 오류 상태는 `transcript_error`/`file_error`.

## 다음 할 일

1. 사용자가 `DAGLO_API_TOKEN` 설정 + 1~2분짜리 짧은 녹음 파일 준비(`recordings/` 아래 권장, gitignore 됨) → `py -3.12 daglo.py recordings/<파일>` 실행. 새 터미널이 아니면 PATH 미반영일 수 있으니 `python` 대신 `py -3.12` 사용.
2. 실행 결과 확인: 업로드 성공 여부, `words[]`에 `speaker`·시각이 들어오는지. 안 들어오면 `daglo.py`의 `request_transcript()`에서 `sttConfig` 전달 방식을 고친다.
3. 실제 응답 구조가 확인되면 그 응답을 고정 표본으로 삼아 2단계(단어 목록 → `발언 번호 / 시각 / 화자 / 내용` 원문)와 그 자동 테스트를 만든다.
4. 계획을 더 세우기 전에 명세서의 남은 미정 3개를 사용자에게 질문한다: 회의 날짜 출처 / 노션 회의록 DB 구성과 원문 위치 / LLM 제공자와 모델.
5. 이번 세션 변경분 커밋 (사용자가 요청할 때).

## 결정과 이유

- 녹음은 다글로에 multipart로 직접 올린다. S3 서명 URL·URL 방식은 쓰지 않는다 — API가 직접 업로드를 지원하고, 녹음을 외부 URL에 둘 필요가 없어진다.
- 비동기(긴 음성) API + 폴링 사용 — 동기 API는 30초 이하만 받는다. 콜백은 서버가 필요해서 "서버를 만들지 않는다"는 명세와 맞지 않는다.
- 화자 분리는 `sttConfig.speakerDiarization.enable=true`, 언어는 `ko-KR`. `speakerCountHint`는 넣지 않았다(참석자 수를 입력받지 않으므로).
- 회의 ID = 녹음 파일 sha256 앞 16자, 단계 산출물은 `runs/<회의ID>/`에 파일로 둔다 — 명세의 "실패한 단계부터 다시 실행" 요구 때문.
- 업로드 직후 `rid`를 파일로 남긴다 — 업로드는 크레딧을 쓰므로 폴링 실패 시 재업로드를 피하려고. (신규 계정 무료 크레딧은 비동기 약 10시간, FAQ 기준.)
- 의존성은 `requests` 하나 — multipart 업로드를 표준 라이브러리로 직접 짜지 않으려고.
- `docs/spec.md` 버전 표기는 v0.6 그대로 뒀다. 올릴지는 사용자 결정.

## 시도했다가 실패한 것

- WebFetch로 API Reference(`apis.daglo.ai/en/docs`) 읽기 — JS로 렌더링되는 페이지라 제목만 나왔다. 내장 브라우저로 열어서 읽었다. multipart 스키마는 Body 콘텐츠 타입 select를 바꿔야 보인다.
- 설치 전 `python`/`python3` 실행 — MS Store 안내용 껍데기(앱 실행 별칭)라 실패. 지금은 `py -3.12`로 실행된다.

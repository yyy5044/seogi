# 진행 상황 (2026-09-21 갱신, 두 번째)

## 목표

회의 녹음 파일 하나를 넣으면 사람 개입 없이 회의록 정리본이 노션에 올라가는 명령줄 Python 스크립트 (`docs/spec.md`, v0.6).
지금까지 1단계(다글로 API 음성 인식)만 만들었고, 실제 녹음으로 동작을 확인했다.
`docs/spec.md`는 사용자가 브레인스토밍한 것을 AI가 받아 적은 문서라 계속 바뀔 수 있다.

## 완료

- 1단계 `daglo.py`: 실제 녹음으로 다글로 API 호출 성공 — 확인 방법: `py -3.12 daglo.py "recording\21일 점심회의-1-1.m4a"` 직접 실행(2분, 1.98MB. 실행 뒤 사용자가 폴더 이름을 `recordings`로 바꿨다). multipart 업로드 → `rid` 수신 → 상태 `ai_requested → transcribing → transcribed` → 11초 만에 완료. `runs/2bfc0703de20ad5a/`에 `stt_response.json`, `transcript.txt`(758자), `stt_rid.txt` 생성. 코드 커밋 `264dfdf`.
- 화자 분리 동작 확인 — 단어 210개 전부에 `speaker`가 붙었고 화자 4명으로 나뉨. 즉 `sttConfig`를 multipart 폼 필드에 JSON 문자열로 넣는 방식이 맞다(문서에 예제가 없어 추정이었던 부분).
- 다글로 응답 구조 확정 (실제 응답으로 확인):
  ```json
  {"rid": "...", "status": "transcribed", "progress": 100,
   "sttResults": [{"transcript": "전체 텍스트",
     "words": [{"speaker": "1", "word": "보면은",
                "startTime": {"seconds": "0", "nanos": 830000000},
                "endTime": {"seconds": "1", "nanos": 109999999},
                "segmentId": "1"}]}]}
  ```
  주의: `seconds`·`speaker`·`segmentId`는 **문자열**, `nanos`만 정수. 단어 앞에 공백이 붙어 온다(`" 네"`) → 이어 붙일 때 구분자 없이 합친다. 이 표본에서 `sttResults`는 1개, `segmentId`는 81종.
- 명세서 미정 1번 해결 → `docs/spec.md` 반영(파일 직접 업로드, S3 미사용) — 커밋 `264dfdf`.
- `README.md`에 새 컴퓨터 설정 안내(파이썬, pip, 환경 변수 표, `setx`) — 커밋 `b1d62ea`.
- 위 커밋은 모두 `origin/main`(https://github.com/yyy5044/seogi.git)에 푸시됨 — 확인 방법: `git status -sb`가 `## main...origin/main`.

## 진행 중

없음. 2단계 이후는 아직 시작하지 않았다.

## 다음 할 일

1. **`daglo.py` 흐름 파악 (사용자 학습 시간).** 사용자가 스크립트를 읽고 이해하려 한다. 목적은 코드 레벨 이해가 아니라 flow 파악이다. 요청받으면 줄 단위 해설이 아니라 단계 흐름(해시로 회의 ID → 기존 결과/`rid` 확인 → 업로드 → 폴링 → 파일 저장)과 "왜 그렇게 했는지" 중심으로 설명한다. 이게 끝나기 전에 새 코드를 먼저 밀어붙이지 않는다.
2. 다른 컴퓨터에서 작업한다면 환경부터: README의 "새 컴퓨터에서 시작할 때" 참고. `DAGLO_API_TOKEN`은 컴퓨터마다 `setx`로 다시 설정해야 하고, `runs/`·`recordings/`는 gitignore라 그 컴퓨터에는 없다(녹음을 다시 돌려야 표본이 생긴다).
3. 2단계(단어 목록 → `발언 번호 / 시각 / 화자 / 내용` 원문) 구현 + 자동 테스트(화자가 바뀌면 발언이 끊긴다 / 빈 입력에서 죽지 않는다). 위 "응답 구조"를 기준으로 고정 표본을 만든다. 테스트 표본은 실제 회의 내용 대신 지어낸 짧은 단어 목록으로 만든다(원문은 저장소에 올리지 않는다는 명세 때문).
   - 미확인: 다글로의 `segmentId` 경계가 화자 전환과 일치하는지. 발언을 `segmentId`로 끊을지 `speaker` 변화로 끊을지 정하기 전에 실제 응답에서 확인한다.
4. 계획을 더 세우기 전에 명세서의 남은 미정 3개를 사용자에게 질문한다: 회의 날짜 출처 / 노션 회의록 DB 구성과 원문 위치 / LLM 제공자와 모델.

## 결정과 이유

- 녹음은 다글로에 multipart로 직접 올린다. S3 서명 URL·URL 방식은 쓰지 않는다 — API가 직접 업로드를 지원하고(실행으로 확인), 녹음을 외부 URL에 둘 필요가 없다.
- 비동기(긴 음성) API + 폴링 — 동기 API는 30초 이하만 받고, 콜백은 서버가 필요해 "서버를 만들지 않는다"는 명세와 맞지 않는다.
- 화자 분리 `speakerDiarization.enable=true`, 언어 `ko-KR`. `speakerCountHint`는 넣지 않는다(참석자 수를 입력받지 않으므로).
- 회의 ID = 녹음 파일 sha256 앞 16자, 단계 산출물은 `runs/<회의ID>/` — "실패한 단계부터 다시 실행" 요구 때문. 파일 이름·위치가 바뀌어도 내용이 같으면 같은 회의다.
- 업로드 직후 `rid`를 `stt_rid.txt`로 남긴다 — 업로드는 크레딧을 쓰므로 재업로드를 피하려고. 결과 파일이 이미 있으면 API를 부르지 않는다. (신규 계정 무료 크레딧은 비동기 약 10시간, FAQ 기준.)
- CER(인식 오류율) 측정은 지금 하지 않는다 — 사용자 결정. 결과가 읽을 만하게 나오는 것만 확인했다. 고유명사·뭉개진 발음에서 오인식이 보였고(예: "짜갱이", "주제선"), 나중에 필요하면 `sttConfig.keywordBoost`를 검토한다.
- API 토큰은 사용자가 직접 `setx`로 설정한다. 에이전트는 토큰 값을 입력·출력하지 않고, 있는지 여부만 확인한다.
- 새 컴퓨터 설정 안내는 `README.md`에 둔다 — progress.md는 매번 다시 쓰는 세션 상태라 고정 안내를 두기에 맞지 않는다.
- `docs/spec.md` 버전 표기는 v0.6 그대로. 올릴지는 사용자 결정.
- 커밋은 `main`에 직접 한다 — 개인 저장소이고 사용자가 다른 컴퓨터에서 `main`을 바로 받아 쓰려는 용도.

## 시도했다가 실패한 것

- WebFetch로 API Reference(`apis.daglo.ai/en/docs`) 읽기 — JS 렌더링 페이지라 제목만 나온다. 내장 브라우저로 열어야 하고, multipart 스키마는 Body 콘텐츠 타입 select를 바꿔야 보인다.
- PowerShell에서 `py -c @'...'@`로 여러 줄 파이썬 실행 — 네이티브 exe로 넘길 때 안쪽 큰따옴표가 사라져 SyntaxError. 스크립트를 파일로 저장해서 실행하면 된다.
- `setx` 이전에 켜 둔 앱/터미널에서는 `$env:DAGLO_API_TOKEN`이 비어 있다. 그 세션에서는 `$env:DAGLO_API_TOKEN = [Environment]::GetEnvironmentVariable('DAGLO_API_TOKEN','User')`로 불러온 뒤 실행하면 된다(값은 출력하지 않는다). 새 PATH도 같은 방식으로 불러와야 `py`가 잡힌다.

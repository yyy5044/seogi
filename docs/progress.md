# 진행 상황 (2026-09-25 갱신)

## 목표

회의 녹음 파일 하나를 넣으면 사람 개입 없이 회의록 정리본이 노션에 올라가는 명령줄 Python 스크립트 (`docs/spec.md`, v0.6).
5단계 중 1단계(다글로 음성 인식)와 2단계(원문 만들기)가 끝났고, 둘 다 실제 녹음으로 동작을 확인했다.
`docs/spec.md`는 사용자가 브레인스토밍한 것을 AI가 받아 적은 문서라 계속 바뀔 수 있다.

작업 방식: 사용자는 각 스크립트를 코드 레벨이 아니라 흐름(flow) 중심으로 이해하고 넘어가길 원한다. 새 스크립트를 만들면 함수별 역할을 설명하는 시간을 가진 뒤 다음 단계로 간다. 혼자 하는 프로젝트라 PR은 쓰지 않고 `main`에 직접 커밋한다.

## 완료

- **1단계 `daglo.py`**: 다글로 비동기 STT에 녹음을 multipart로 직접 업로드 → 폴링 → `runs/<회의ID>/stt_response.json`, `transcript.txt`, `stt_rid.txt` 저장. 커밋 `264dfdf`. 확인: 실제 녹음(`recordings/21일 점심회의-1-1.m4a`, 2분, 1.98MB)으로 11초 만에 변환, 화자 4명 분리됨. 사용자가 흐름 파악을 마쳤고 학습 주석을 추가함(`ab9ae14`, `b271e04`).
- **2단계 `transcript.py`**: `stt_response.json`의 단어 목록을 화자가 바뀌는 지점에서 끊어 발언 목록으로 만들고 `runs/<회의ID>/transcript.md`(`| 번호 | 시각 | 화자 | 내용 |` 표)와 `utterances.json`(같은 내용, 뒤 단계용 원본)을 저장. 커밋 `006ab85`. 확인: 실제 응답으로 `단어 210개 → 발언 23개`, 표본 분석으로 미리 계산한 23개와 일치. 사용자가 함수별 설명을 듣고 이해함.
- **2단계 자동 테스트 `test_transcript.py`**: 9개 전부 통과 — 확인: `py -3.12 -W error -m unittest test_transcript` → `OK`. 명세서 항목(화자가 바뀌면 발언이 끊긴다 / 빈 입력에서 죽지 않는다) + 추가(같은 화자가 돌아와도 별개 발언 / 마지막 발언 유지 / 시각은 첫 단어 기준 / 표 형식 / 빈 `sttResults`). 표본은 지어낸 단어 목록이다.
- 다글로 응답 구조 (실제 응답으로 확인): `{"rid","status","progress","sttResults":[{"transcript","words":[{"speaker":"1","word":" 네","startTime":{"seconds":"0","nanos":830000000},"endTime":{...},"segmentId":"1"}]}]}`. `seconds`·`speaker`·`segmentId`는 **문자열**, `nanos`만 정수. 단어 앞에 공백이 붙어 온다.
- `segmentId` 조사 완료 → 쓰지 않기로 결정 (아래 "결정과 이유"). 명세서 미정 1번(업로드 방식)도 해결되어 `spec.md`에 반영됨(`264dfdf`).
- `README.md`에 새 컴퓨터 설정 안내(파이썬, pip, 환경 변수 표, `setx`) — `b1d62ea`.
- 모든 커밋이 `origin/main`(https://github.com/yyy5044/seogi.git)에 푸시됨. 확인: `git status -sb` → `## main...origin/main`, 작업 트리 깨끗함.

## 진행 중

없음. 3단계 이후는 시작하지 않았다.

## 다음 할 일

1. **명세서 미정 중 "LLM 제공자와 모델" 결정** — 3단계 코드를 쓰기 전에 반드시 필요하다. 사용자에게 질문한다. 결정되면 API 키 환경 변수 이름을 정하고 `README.md`의 환경 변수 표에 한 줄 추가한다. (Anthropic/Claude를 쓰게 되면 `claude-api` 스킬을 먼저 읽는다.)
2. **3단계 LLM 추출** — 입력 `runs/<회의ID>/transcript.md`(또는 `utterances.json`), 출력 `runs/<회의ID>/extraction.json`(제목·안건·결정사항·할 일). 결정사항과 할 일에는 근거 발언 번호(`no`)를 함께 적게 한다. LLM 호출은 1회. 외부 서비스 파일 규칙에 따라 `llm.py` 같은 파일 하나로 분리한다. 작성 후 사용자에게 함수별 흐름 설명.
3. **4단계 근거 검증** — `extraction.json`의 근거 번호가 `utterances.json`에 실제로 있는지 코드로 확인. 없으면 정리본에서 빼고 제외 목록에 남긴다. 정리본에는 근거를 해당 발언의 시각으로 표시. 자동 테스트(가짜 근거 번호 항목이 제외된다 / 정상 항목은 통과한다)는 명세서 완료 기준이다.
4. 5단계 전에 남은 미정 2개 질문: 회의 날짜 출처 / 노션 회의록 DB 구성과 원문 위치(본문·토글·하위 페이지).
5. `daglo.py` 보강(사용자가 주석으로 지적한 약점): 첫 실행에서 `stt_rid.txt`만 남고 다글로 쪽 작업이 실패하면 재실행 때 계속 실패한 `rid`만 조회한다. 실패 상태를 받으면 `stt_rid.txt`를 지우거나 재업로드하도록 고친다. 급하지 않음.
6. 다른 컴퓨터에서 작업할 때: README의 "새 컴퓨터에서 시작할 때" 참고. `DAGLO_API_TOKEN`은 컴퓨터마다 `setx`로 다시 설정. `runs/`·`recordings/`는 gitignore라 그 컴퓨터에는 없다 → 녹음을 `daglo.py`로 다시 돌려야 표본이 생긴다(크레딧 소모).

## 결정과 이유

- **발언은 화자가 바뀌는 지점에서 끊는다. `segmentId`는 쓰지 않는다.** 다글로 OpenAPI 명세 원본(`https://apis.daglo.ai/en/openapi.prod.en.yaml`, 한글판 `openapi.prod.yaml`)의 `words` 스키마에 정의된 필드는 `word`, `speaker`, `startTime`, `endTime`, `hasKeyword` 다섯 개뿐이고 `segmentId`는 파일 전체에 한 번도 안 나온다. 가이드 페이지 예제 JSON에만 정의 없이 등장한다. 실제 데이터에서는 세그먼트 81개(평균 2.6단어)로 "발언"보다 훨씬 작은 인식 구간이었고, 화자가 섞인 세그먼트는 0개, 화자 전환 22곳 모두 세그먼트 경계와 일치했다. 즉 틀린 필드는 아니지만 문서 근거가 없고 원하는 단위도 아니다. 화자 기준은 문서에 정의된 `speaker`만 쓰고 명세서 테스트 규칙과도 같다.
- 짧은 맞장구("네, 네")도 발언 하나로 그대로 남긴다. 합치거나 걸러내지 않는다 — 원문은 검수용이므로 대화 흐름 그대로가 맞다.
- 2단계 산출물을 `transcript.md`(LLM 입력·노션 본문용 표)와 `utterances.json`(4단계 대조용 원본) 둘로 낸다 — 표 파싱 없이 번호를 찾게 하려고.
- 테스트는 표준 라이브러리 `unittest` — 추가 설치 없음. 표본은 실제 회의 내용 대신 지어낸 단어(원문은 저장소에 올리지 않는다는 명세).
- 시각 표시는 `mm:ss`, 한 시간 넘으면 `h:mm:ss`. 소수점은 버린다.
- 파일 이름: 외부 서비스는 서비스명(`daglo.py`, 나중에 `notion.py`, `llm.py`), 일반 코드 단계는 역할명(`transcript.py`).
- 녹음은 다글로에 multipart로 직접 올린다(S3·URL 방식 안 씀). 비동기 API + 폴링(동기는 30초 제한, 콜백은 서버 필요). 화자 분리 on, `ko-KR`, `speakerCountHint` 없음.
- 회의 ID = 녹음 파일 sha256 앞 16자. 업로드 직후 `rid`를 저장해 재업로드(과금)를 피한다. 결과 파일이 있으면 API를 부르지 않는다.
- CER(인식 오류율) 측정은 하지 않는다 — 사용자 결정. 고유명사 오인식이 보였고 필요하면 `keywordBoost` 검토.
- API 토큰은 사용자가 직접 `setx`. 에이전트는 값을 입력·출력하지 않고 있는지만 확인한다.
- PR을 쓰지 않고 `main` 직접 커밋 — 혼자 하는 프로젝트. GitHub CLI(`gh`)는 설치되어 있지만 로그인 안 됨, 당장 필요 없음.
- `docs/spec.md` 버전 표기는 v0.6 그대로.

## 시도했다가 실패한 것

- `daglo.py`의 `segmentId`를 발언 단위로 쓰려던 계획 — 위 이유로 폐기.
- WebFetch로 API Reference(`apis.daglo.ai/en/docs`) 읽기 — JS 렌더링이라 제목만 나온다. 내장 브라우저로 열거나, 페이지가 불러오는 OpenAPI yaml을 `curl`로 직접 받는 게 빠르다.
- 앱의 "Create PR" 버튼을 실수로 눌러 브랜치 `docs/daglo-flow-notes`가 생겼음 — `main`에 ff 머지 후 로컬·원격 브랜치 삭제. `gh`는 이때 설치됨.
- Bash heredoc으로 파이썬 파일을 쓸 때 `"\\|"`가 `"\|"`로 들어가 SyntaxWarning — Edit 도구로 고쳤다. 이스케이프가 있는 코드는 heredoc보다 Write/Edit이 안전하다.
- PowerShell에서 `py -c @'...'@`로 여러 줄 파이썬 실행 — 큰따옴표가 사라져 SyntaxError. 스크립트를 파일로 저장해 실행한다.
- `setx` 이전에 켜 둔 앱/터미널에서는 `$env:DAGLO_API_TOKEN`이 비어 있다 — `[Environment]::GetEnvironmentVariable('DAGLO_API_TOKEN','User')`로 불러온 뒤 실행(값은 출력하지 않음). 새 PATH도 같은 방식으로 불러와야 `py`가 잡힌다. Git Bash에서는 `py -3.12`가 바로 잡힌다.

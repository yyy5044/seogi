# 진행 상황 (2026-09-25 갱신, 여섯 번째)

## 목표

회의 녹음 파일 하나를 넣으면 사람 개입 없이 회의록 정리본이 노션에 올라가는 명령줄 Python 스크립트 (`docs/spec.md`, v0.6).
**5단계 전부 완성, 명세서 완료 기준 충족.** 실제 녹음 2개(2분, 50분)로 `run.py` 한 번에 노션 페이지가 생기는 것을 실행 확인했다. 이후는 폴더 정리, 다글로 옵션 실험 2개(둘 다 쓸모없음 확인), 다음 개선(교정 단계, 화자 처리)의 토론과 계획 수립. 코드 변경은 없었다.
`docs/spec.md`는 사용자가 브레인스토밍한 것을 AI가 받아 적은 문서라 계속 바뀔 수 있다.

작업 방식: 사용자는 각 스크립트를 코드 레벨이 아니라 흐름(flow) 중심으로 이해하고 넘어가길 원한다. 새 스크립트를 만들면 함수별 역할을 설명하는 시간을 가진 뒤 다음 단계로 간다. 혼자 하는 프로젝트라 PR은 쓰지 않고 `main`에 직접 커밋한다. 커밋·push는 사용자가 시킬 때 한다. 문서에는 사용자가 적으라고 한 내용만 넣고, 제안은 채팅으로 한다. 폴더 구조는 루트 `README.md`의 트리를 참고. 설계는 채팅으로 제안해 사용자 확인을 받은 뒤 구현한다.

**용어 (`docs/spec.md` "용어" 절)**: 테스트 = 자동 실행·통과/실패(`tests/`). 실험 = 조건을 바꿔 측정·비교·결론, 보고서(`experiments/`). 실행 확인 = 실제 데이터로 한 번 돌려 되는지 봄(`run.py` 실제 녹음). 셋을 "테스트"로 뭉뚱그리지 않는다.

## 완료

- **파이프라인 5단계 + `run.py`** (커밋 `7cda950`까지, 요약 규칙 `275d2b8`): `daglo.py`(다글로 STT, `recording.json`에 녹음 이름·수정 시각) → `transcript.py`(화자 전환 기준 발언, `transcript.md`·`utterances.json`) → `llm.py`(Claude `claude-opus-5-5`, `effort="high"`, JSON 스키마, `extraction.json`: `title`/`summary`/`topics`/`decisions[{text,evidence}]`/`todos[{text,evidence,owner,due}]`, 프롬프트 `prompts/extract.md`) → `verify.py`(근거 번호 대조, 하나라도 없으면 항목 전체 제외, `minutes.md`·`verified.json`·`excluded.json`) → `notion.py`(회의록 DB 페이지, 회의 ID 중복 방지, 제목 `YYYY-MM-DD`/` (n)`, 하위 페이지 "원문" 표 99행씩). 실행 확인: 50분 녹음 `run.py` 78초 무개입, 노션 페이지 MCP로 읽어 속성·본문·표 341행 확인. 3단계 50분 기준 85초·$0.30·요약 4,810자 14문단.
- **노션 회의록 DB**: https://app.notion.com/p/4d21d183ff2541f7866cd33220a57883 (개인 공간). 속성: 회의(제목), 회의일, 상태(자동 생성(미검수)/검수 완료), 회의 ID, 녹음 파일, 생성 시각. 데이터 소스 ID `5ed30c30-e1eb-45b8-8604-b645fd57d8b3`. 내부 통합 연결 완료. 50분 회의 페이지 `3e6b855637d9813e8366fd51680fcd43`.
- **폴더 정리** (`42d39d1`, `251d0a1`): `experiments/<실험명>/`에 스크립트+보고서 평평하게, 파이프라인 테스트는 `tests/`. 확인: `py -3.12 -m unittest` → 58개 `OK`.
- **실험 3개** (`experiments/README.md` 목록). 셋 다 결론이 나 있고 재실험 예정 없음.
  - `stt_compare/`: 다글로 vs CLOVA, CER 10.7% vs 14.4%, 유의미한 차이 없음 → 다글로 유지.
  - `keyword_boost/` (`42d39d1`): 켜면 CER 10.7% → boost 1: 12.7%, boost 7: 14.7~15.5%. 없던 말이 같은 자리에 끼어듦 → 파이프라인에 넣지 않음. 실험용 코드는 커밋 없이 되돌림.
  - `speaker_count_hint/` (`602cb8b`): 50분(8명 잡힘)에 힌트 3·4·5 → 단어 하나까지 힌트 없음과 동일(무시), 힌트 2 → 정확히 2명 강제(텍스트도 바뀜, 2분 CER 10.7→11.8%). 2분(4명)에 3·4도 동일 → 파이프라인에 넣지 않음. 총 7회 호출. 결과 파일 `runs/_experiments/speaker_count_hint/`(gitignore).
- **문서** (`847f46f`, `9852ecd`): `spec.md`에 "용어" 절, "계획: 교정 단계 추가 (아직 만들지 않음)" 절. `README.md` 트리 최신.
- 모든 커밋 `origin/main`에 푸시됨(`602cb8b`). 확인: `git status -sb` → `## main...origin/main`, 작업 트리 깨끗함.

기타 참고:
- 다글로 응답: `sttResults[].words[]` = `{speaker:"1", word:" 네", startTime:{seconds:"0", nanos:...}}`. 다글로 `sttConfig` 옵션 전체: `keywordBoost`, `language`, `model`(`general`뿐), `multiChannel`, `speakerDiarization{enable, speakerCountHint}`, 콜백. 맥락·프롬프트 기능 없음. OpenAPI: `curl https://apis.daglo.ai/en/openapi.prod.en.yaml`.
- `runs/`: `2bfc0703de20ad5a`(2분, 정답 원고 `recordings/21일 점심회의-1-1.정답.txt`), `6965a6464ec7d562`(50분, 참석 5명 중 1명은 과묵해 발언 여부 불확실, 다글로는 8명으로 나눔: 발언 96/94/91/46/6/6/1/1).
- 50분 회의 소수 화자 내용(사용자 판단 대기): 화자5는 "응", "네", "펜 한 번만 빌려주실래요" 등 짧은 말 6개(다섯 번째 참석자일 수도). 화자6은 14:50~17:49 회의 주제와 다른 말 6개(옆 대화 의심). 화자8은 44:31 한 마디 "원근이 말대로 4시간당 30분으로 알고 있거든"(참여자 말로 보임).
- 노션 휴지통 페이지는 조회에 안 잡혀 지우고 다시 올릴 수 있다.

## 진행 중

없음.

## 다음 할 일

1. **`llm.py`, `verify.py`, `notion.py`, `run.py` 흐름 설명.** 사용자가 이 네 파일은 코드를 읽지 않아 로직을 모른다. 함수별 역할을 흐름 중심으로 설명(`daglo.py`, `transcript.py`는 이미 함).
2. **교정 단계 구현** — 설계는 `docs/spec.md` "계획: 교정 단계 추가" 절에 확정(2단계와 추출 사이 `correct.py`, 6단계 재편, STT 원본 보존·노션에 원본 하위 페이지 추가, `prompts/glossary.md` + `--context` 한 줄, `[{no,text}]` 스키마와 번호 검증, 80개씩 분할, `corrections.md`). 만들 때 spec 단계 표·"LLM은 3단계에만"·README·`run.py`·`tests/`를 함께 고친다. 사용자가 "지금은 계획만" 이라고 해서 코드 없음.
3. **화자 처리 방향 결정** (토론만 했고 결정 없음). 사용자 불편: "화자1, 화자2" 표기. 논의 결과: 다글로 옵션으로는 해결 불가(위 실험). 후보 순서 — (a) 2단계에서 발언 n개 이하 화자를 "기타"로 표시(단, 화자8 같은 진짜 한 마디도 기타가 됨), (b) LLM이 호칭·맥락으로 이름 추정 + 근거 발언 번호 제시, 노션에는 번호 유지하고 제안 표만 첨부, 사람이 확인, (c) 목소리 등록 기반 식별(pyannote 등, 며칠 단위, 동의 필요, 소음 녹음 정확도 미확인). 사용자가 소수 화자 내용을 보고 (a) 여부를 정하는 게 먼저. 결정되면 spec "나중에: 화자 이름 붙이기"를 계획으로 바꾼다.
4. 사용자 노션 페이지 검토 후 품질 개선. 발견했지만 손대지 않은 것: 요약 문체가 실행마다 다름("~했다"/"~했습니다", 프롬프트 한 줄로 고정 가능). 회의일이 파일 수정 시각이라 파일을 옮기면 오늘 날짜(사용자 결정: 노션에서 직접 고침). 노션 원문 표가 99행마다 나뉨(API 제한).
5. `daglo.py` 보강(급하지 않음): `stt_rid.txt`만 남고 다글로 작업이 실패하면 재실행 때 실패한 `rid`만 계속 조회. 실패 상태면 `stt_rid.txt` 삭제 또는 재업로드. `experiments/stt_compare/daglo.py` 스냅샷은 건드리지 않는다.
6. 다른 컴퓨터: `README.md` "새 컴퓨터에서 시작할 때". 환경 변수 6개(`DAGLO_API_TOKEN`, `CLOVA_SPEECH_SECRET`, `CLOVA_SPEECH_INVOKE_URL`, `ANTHROPIC_API_KEY`, `NOTION_API_KEY`, `NOTION_DATABASE_ID`) `setx`. `runs/`·`recordings/` gitignore.

## 결정과 이유

- **다글로 부가 옵션(키워드 부스팅, 화자 수 힌트)은 쓰지 않는다**: 실험 결과 둘 다 효과 없거나 악화. 기본 인식·화자 분리만 쓰고 나머지(오탈자, 화자)는 우리 코드·LLM에서 처리. 다글로 무료 크레딧이 넉넉해(2026-09-25 기준 약 11,000원) 실험 비용은 부담 없음.
- **교정 단계는 별도 단계로, STT 원본은 보존**: 제안은 "3단계에 맥락만 제공"이었으나 사용자가 "노션 원문을 사람이 읽으니 교정본이 필요하고 요약도 그걸로" 라고 결정. 원본 보존과 `corrections.md`(고친 목록)로 "안 한 말로 고치는" 위험을 보완.
- **의미 없다고 결론 난 기능 코드는 커밋하지 않는다**: 키워드 부스팅 코드를 되돌리고 실험 기록만 남김. 사용자 지적.
- **실험은 `experiments/<실험명>/` 하나에 스크립트+보고서 평평하게, 스크립트는 자체 완결**(다른 실험 폴더에 기대지 않음, CER 측정 `stt_compare/cer.py`만 공용). 결과 파일은 `runs/_experiments/<실험명>/`.
- **파이프라인 테스트는 `tests/`**, 실험용 `test_cer.py`는 실험 폴더에.
- **용어 세 가지(테스트/실험/실행 확인)를 `spec.md`에 명시**.
- **LLM은 Claude `claude-opus-5-5`**(`ca17c50`): 20% 저렴, 같은 회의에서 더 보수적 추출, 사용자가 더 정확하다고 판단. `effort="high"` 명시(5.5 기본은 medium).
- **요약은 원문 대체용 서술**(`275d2b8`): 길이 제한 없음, 흐름 순서·주제별 문단. **"안건"이 아니라 "대화 주제"(`topics`)**.
- **4단계는 근거 일부만 가짜여도 항목 전체 제외**. **5단계 회의일 = 녹음 수정 시각, 제목 = 회의일(+` (n)`), 회의 ID 속성, 원문은 하위 페이지**: 사용자 결정.
- **노션은 `requests`로 REST 직접 호출**, API `2025-09-03`(부모 `data_source_id`, 조회 `POST /data_sources/{id}/query`). rich_text 2,000자·블록 100개·표 99행 분할.
- **음성 인식은 다글로 유지**(`experiments/stt_compare/decision.md`).
- 터미널 출력에 cp949 밖 문자(`≈`, `—`) 안 씀. 테스트는 함수 하나가 규칙 하나. 발언은 화자 전환에서 끊음, `segmentId` 안 씀. 파일 이름: 외부 서비스는 서비스명, 일반 코드는 역할명. 회의 ID = sha256 앞 16자. API 키는 사용자가 `setx`, 에이전트는 값 출력 안 함, 켜 둔 앱에서는 `[Environment]::GetEnvironmentVariable(이름,'User')`. `requirements.txt`는 `requests`, `anthropic`. `spec.md` v0.6 유지.

## 시도했다가 실패한 것

- **키워드 부스팅** — 어떤 강도에서도 CER 악화. 코드 되돌림.
- **`speakerCountHint`** — 3 이상 무시, 2는 2명 강제. 과분리 해결 불가.
- Bash heredoc 안의 `\\n`이 실제 줄바꿈으로 들어가 SyntaxError(누적 네 번). 파이썬 문자열에 `\n`이 있는 코드는 Write/Edit 도구로.
- Bash 콘솔은 cp949라 한글 출력이 깨짐 — `PYTHONUTF8=1` 또는 `cat`.
- 요약 "3~5문장" 제한 — 50분 회의도 5문장. 제한 제거.
- `llm.py`의 `≈` — cp949 `UnicodeEncodeError`. `약`으로 교체.
- PowerShell 여러 줄 파이썬은 `Set-Content -Encoding utf8`로 파일에 쓴 뒤 실행.
- 정답 원고 루트 배치 → `recordings/`로 이동, BOM 제거. 첫 CER 43.6%(표 마크업 포함) → 표 인식 추가. 발언별 CER·`segmentId` 발언 단위 폐기. WebFetch로 JS 페이지(다글로 API Reference) 읽기 실패 → OpenAPI yaml `curl`. 노션 개발자 문서는 WebFetch로 읽힘. 앱 "Create PR" 실수 → ff 머지 후 브랜치 삭제.

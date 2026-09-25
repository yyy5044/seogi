# seogi

회의 녹음 파일을 넣으면 회의록 정리본이 노션에 올라가는 명령줄 도구. 명세는 [docs/spec.md](docs/spec.md), 현재 진행 상황은 [docs/progress.md](docs/progress.md).

## 새 컴퓨터에서 시작할 때

API 키는 저장소에 없고 컴퓨터마다 환경 변수로 따로 설정해야 한다.

1. Python 3.12 설치: `winget install Python.Python.3.12`
2. 의존성 설치: `py -3.12 -m pip install -r requirements.txt`
3. 환경 변수 설정 (PowerShell, 아무 경로에서나). 설정 후 터미널과 앱을 새로 열어야 적용된다.

   | 변수 | 용도 | 발급처 |
   |---|---|---|
   | `DAGLO_API_TOKEN` | 다글로 STT API | https://developers.daglo.ai/console → 토큰 메뉴 |
   | `CLOVA_SPEECH_SECRET` | 네이버 CLOVA Speech (인식률 비교용) | 네이버 클라우드 콘솔 → CLOVA Speech → 도메인 → 설정 → 연동 정보 → Secret Key |
   | `CLOVA_SPEECH_INVOKE_URL` | 같은 곳 | 같은 화면의 Invoke URL |
   | `ANTHROPIC_API_KEY` | Claude API (3단계 추출) | https://console.anthropic.com → API Keys (선불 크레딧 충전 필요) |
   | `NOTION_API_KEY` | 노션 API (5단계 기록) | https://www.notion.so/profile/integrations → 새 내부 통합 → 시크릿. 그 다음 회의록 DB 페이지 우상단 `...` → 연결 → 이 통합을 추가해야 스크립트가 DB에 접근할 수 있다 |
   | `NOTION_DATABASE_ID` | 회의록 DB | DB 페이지 주소 `notion.so/...` 끝의 32자리 (예: `4d21d183ff2541f7866cd33220a57883`) |

   ```powershell
   setx DAGLO_API_TOKEN "토큰"
   ```

4. 설정 확인 (값은 출력하지 않는다): `[bool]$env:DAGLO_API_TOKEN`

## 실행

저장소 루트에서 실행한다. 결과는 `runs/<회의ID>/`에 저장된다.

```powershell
py -3.12 daglo.py recordings/<녹음 파일>      # 1단계: 음성 인식 → stt_response.json
py -3.12 transcript.py runs/<회의ID>          # 2단계: 발언 단위 원문 → transcript.md, utterances.json
py -3.12 llm.py runs/<회의ID>                 # 3단계: Claude 추출 → extraction.json, extraction_review.md (--force: 다시 호출)
py -3.12 verify.py runs/<회의ID>              # 4단계: 근거 검증 → minutes.md(정리본), verified.json, excluded.json(제외 목록)
py -3.12 notion.py runs/<회의ID>              # 5단계: 노션 회의록 DB에 페이지 생성 (같은 회의 ID면 다시 만들지 않음)
py -3.12 run.py recordings/<녹음 파일>        # 1~5단계 한 번에
py -3.12 -m unittest -v                       # 테스트
```

## 폴더 구조

```
seogi/
├─ README.md               이 파일. 설치·실행법과 폴더 구조
├─ CLAUDE.md               Claude Code 작업 규칙 (세션 시작 시 progress.md 먼저 읽기 등)
├─ requirements.txt        외부 라이브러리 목록 (requests, anthropic)
├─ .gitignore              키·녹음·원문·runs/·캐시를 저장소에서 제외
│
├─ run.py                  전체 실행. 녹음 파일 하나로 1~5단계를 차례로 부르고 단계별 소요 시간 출력
├─ daglo.py                1단계 음성 인식. 녹음을 다글로 API에 올려 runs/<회의ID>/stt_response.json, recording.json(녹음 이름·수정 시각) 저장
├─ transcript.py           2단계 원문 만들기. 단어 목록을 화자 기준 발언으로 묶어 transcript.md, utterances.json 저장
├─ llm.py                  3단계 추출. transcript.md를 Claude에 보내 extraction.json(근거 번호 포함), extraction_review.md 저장
├─ verify.py               4단계 근거 검증. extraction.json의 근거 번호를 utterances.json과 대조해 minutes.md(근거를 시각으로 표시), verified.json, excluded.json 저장
├─ notion.py               5단계 노션 기록. 회의록 DB에 페이지 1개(요약→대화 주제→결정사항→할 일→제외 목록), 하위 페이지 '원문'에 발언 표
│
├─ tests/                  파이프라인 테스트 (API 호출 없음). 루트에서 py -3.12 -m unittest 로 전부 실행
│  ├─ test_transcript.py   2단계 9개 (화자 전환 분리, 빈 입력 등)
│  ├─ test_llm.py          3단계 10개 (파싱·검토 파일·재실행 동작)
│  ├─ test_verify.py       4단계 13개 (가짜 근거 번호 항목 제외, 정상 항목 통과, 빈 입력)
│  └─ test_notion.py       5단계 16개 (블록 생성, 제목 번호, 중복 방지)
│
├─ prompts/
│  └─ extract.md           3단계 시스템 프롬프트. 추출 결과를 다듬을 때 이 파일을 고친다
│
├─ docs/
│  ├─ spec.md              명세서. 만들 것, 단계, 지킬 것, 완료 기준, 미정 항목
│  └─ progress.md          진행 상황. /handoff 때만 갱신, 새 세션은 이 파일부터 읽음
│
├─ experiments/            실험 기록 (파이프라인 본체 아님). 실험마다 폴더 하나, 당시 스크립트와 보고서 보존
│  ├─ README.md            실험 폴더 규칙과 실험 목록
│  ├─ stt_compare/         다글로 vs CLOVA 인식률 비교 → 다글로 유지
│  │  ├─ daglo.py          실험 시점의 루트 daglo.py 복사본
│  │  ├─ clova.py          네이버 CLOVA Speech 호출
│  │  ├─ cer.py            정답 원고 vs 인식 결과 CER 계산 (다른 실험도 씀)
│  │  ├─ test_cer.py       cer.py 테스트 10개
│  │  ├─ results.md        실험 결과 (측정한 사실만)
│  │  └─ decision.md       다글로 유지 결정과 근거, 비용 비교
│  ├─ keyword_boost/       다글로 키워드 부스팅 효과 → 켜면 CER 악화, 파이프라인에 넣지 않음
│  │  ├─ keyword_boost.py  부스팅 켜고/끄고 인식해 텍스트로 저장
│  │  └─ report.md         실험 보고서
│  └─ speaker_count_hint/  다글로 화자 수 힌트 → 3 이상 무시, 2는 2명 강제. 파이프라인에 넣지 않음
│     ├─ speaker_count_hint.py  힌트 값을 바꿔 인식하고 화자별 발언·단어 수 출력
│     └─ report.md         실험 보고서
│
├─ .claude/skills/handoff/ /handoff 명령 정의 (progress.md 갱신 절차)
│
├─ recordings/             녹음 파일, 직접 받아쓴 정답 원고 (저장소에 안 올림)
└─ runs/<회의ID>/          단계별 실행 결과. 회의 ID는 녹음 파일 해시 (저장소에 안 올림)
```

`__init__.py`는 폴더를 파이썬 패키지로 표시하는 빈 파일이고, `__pycache__/`는 파이썬이 만드는 캐시라 둘 다 설명에서 뺐다.

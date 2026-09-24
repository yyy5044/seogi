# stt_eval — 음성 인식 서비스 비교 실험

회의록 파이프라인 1단계에 어느 STT를 쓸지 정하기 위한 실험 기록. 파이프라인 본체가 아니며, 회의록 생성에는 쓰이지 않는다.

이 폴더의 스크립트는 **실험 당시 상태를 그대로 보존**한다. 루트의 `daglo.py`가 나중에 바뀌어도 여기 있는 것은 고치지 않는다. 나중에 동작하지 않아도 상관없다. "그때 무엇으로 측정했는가"의 기록이 목적이다.

## 구성

```
stt_eval/
├─ README.md            이 파일
├─ scripts/             음성 인식·측정 스크립트 (실험 당시 스냅샷)
│  ├─ daglo.py          다글로 STT 호출. 실험 시점(2026-09-25)의 루트 daglo.py 복사본
│  ├─ clova.py          네이버 CLOVA Speech 장문 인식 호출. 같은 폴더의 daglo.py에서 회의 ID 함수를 가져다 쓴다
│  └─ cer.py            정답 원고 vs 인식 결과의 CER(문자 오류율) 계산
├─ tests/
│  └─ test_cer.py       cer.py 테스트 10개
└─ docs/
   ├─ results.md        실험 결과 — 표본, CER, 오류 유형, 한계. 측정한 사실만
   └─ decision.md       선택 결정 — 근거, 비용 비교, 다시 볼 조건
```

결과 파일(`runs/<회의ID>/clova_response.json`, `clova_transcript.txt`)과 정답 원고(`recordings/*.정답.txt`)는 회의 원문이므로 저장소에 올리지 않는다.

## 실행 (모두 저장소 루트에서)

```powershell
# 1. 다글로 결과 (루트 daglo.py 또는 스냅샷, 이 시점엔 같은 코드)
py -3.12 stt_eval/scripts/daglo.py recordings/<녹음>.m4a

# 2. CLOVA 결과 — CLOVA_SPEECH_SECRET, CLOVA_SPEECH_INVOKE_URL 환경 변수 필요 (루트 README 참고)
py -3.12 stt_eval/scripts/clova.py recordings/<녹음>.m4a

# 3. 정답 원고를 recordings/<녹음>.정답.txt 로 직접 받아쓴 뒤 CER 비교
py -3.12 stt_eval/scripts/cer.py recordings/<녹음>.정답.txt runs/<회의ID>/transcript.txt runs/<회의ID>/clova_transcript.txt

# 테스트 (루트에서 py -3.12 -m unittest 를 돌리면 함께 실행된다)
py -3.12 -m unittest stt_eval.tests.test_cer -v
```

## 정답 원고 쓰는 법

- 녹음을 들으며 실제로 말한 대로 적는다. "어", "그" 같은 군말도 말했으면 적는다.
- 띄어쓰기와 구두점은 신경 쓰지 않아도 된다 (`cer.py`가 비교 전에 지운다).
- 인식 결과를 보면서 고쳐 쓰면 그 서비스에 유리하게 기울 수 있다. 가능하면 결과를 보지 않고 쓴다.
- 표 형식(`| 번호 | 시각 | 화자 | 내용 |`)으로 써도 되고 평문으로 써도 된다.

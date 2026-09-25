"""다글로 speakerCountHint 실험 (2026-09-25 당시 스크립트 보존).

사용법: (저장소 루트에서) python experiments/speaker_count_hint/speaker_count_hint.py <녹음 파일> <출력 이름> [힌트]
  힌트를 0 으로 주거나 생략하면 힌트 없이 요청한다 (대조군).
예:   python experiments/speaker_count_hint/speaker_count_hint.py recordings/x.m4a hint4 4

runs/ 의 회의 폴더는 건드리지 않고 매번 새로 업로드해 인식한다 (회당 과금).
결과는 runs/_experiments/speaker_count_hint/<출력 이름>.json (응답 원본), .txt (인식 텍스트) 에 저장하고,
화자별 발언 수(화자가 바뀔 때마다 발언 하나)와 단어 수를 출력한다.
토큰은 환경 변수 DAGLO_API_TOKEN. 다른 폴더에 기대지 않도록 업로드·폴링 코드를 이 파일에 둔다.
"""

import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

import requests

API_URL = "https://apis.daglo.ai/stt/v1/async/transcripts"
OUT_DIR = Path("runs/_experiments/speaker_count_hint")
POLL_INTERVAL_SEC = 5
POLL_TIMEOUT_SEC = 60 * 60
ERROR_STATUSES = {"transcript_error", "file_error"}


def _headers() -> dict:
    token = os.environ.get("DAGLO_API_TOKEN")
    if not token:
        sys.exit("환경 변수 DAGLO_API_TOKEN 이 없습니다.")
    return {"Authorization": f"Bearer {token}"}


def wait_result(rid: str) -> dict:
    deadline = time.monotonic() + POLL_TIMEOUT_SEC
    last_status = None
    while time.monotonic() < deadline:
        res = requests.get(f"{API_URL}/{rid}", headers=_headers(), timeout=60)
        if not res.ok:
            sys.exit(f"결과 조회 실패: HTTP {res.status_code} {res.text}")
        body = res.json()
        status = body.get("status")
        if status != last_status:
            print(f"  상태: {status}")
            last_status = status
        if status == "transcribed":
            return body
        if status in ERROR_STATUSES:
            sys.exit(f"변환 실패: {json.dumps(body, ensure_ascii=False)}")
        time.sleep(POLL_INTERVAL_SEC)
    sys.exit(f"시간 초과: rid={rid}")


def transcribe(audio_path: Path, hint: int) -> dict:
    diarization = {"enable": True}
    if hint > 0:
        diarization["speakerCountHint"] = hint
    stt_config = {"language": "ko-KR", "speakerDiarization": diarization}
    print(f"sttConfig: {json.dumps(stt_config, ensure_ascii=False)}")
    with audio_path.open("rb") as f:
        res = requests.post(
            API_URL, headers=_headers(), files={"file": (audio_path.name, f)},
            data={"sttConfig": json.dumps(stt_config)}, timeout=600,
        )
    if not res.ok:
        sys.exit(f"업로드 실패: HTTP {res.status_code} {res.text}")
    return wait_result(res.json()["rid"])


def speaker_stats(body: dict) -> tuple[Counter, Counter]:
    """응답 원본 → (화자별 발언 수, 화자별 단어 수). 발언은 화자가 바뀔 때마다 하나."""
    words = [w for r in body.get("sttResults", []) for w in r.get("words", [])]
    word_count = Counter(w["speaker"] for w in words)
    utt_count = Counter()
    prev = None
    for w in words:
        if w["speaker"] != prev:
            utt_count[w["speaker"]] += 1
            prev = w["speaker"]
    return utt_count, word_count


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("사용법: python experiments/speaker_count_hint/speaker_count_hint.py <녹음 파일> <출력 이름> [힌트]")
    audio, name = Path(sys.argv[1]), sys.argv[2]
    hint = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    started = time.monotonic()
    body = transcribe(audio, hint)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{name}.json").write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / f"{name}.txt").write_text(
        "\n".join(r.get("transcript", "") for r in body.get("sttResults", [])), encoding="utf-8"
    )
    utt, wc = speaker_stats(body)
    print(f"완료 ({time.monotonic() - started:.0f}초): 화자 {len(wc)}명, 단어 {sum(wc.values())}개")
    for spk in sorted(wc, key=lambda s: -wc[s]):
        print(f"  화자{spk}: 발언 {utt[spk]}개, 단어 {wc[spk]}개")
    print(f"저장: {OUT_DIR / name}.json, .txt")

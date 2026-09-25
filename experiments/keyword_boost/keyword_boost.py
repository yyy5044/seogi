"""다글로 키워드 부스팅 실험 (2026-09-25 당시 스크립트 보존).

사용법: (저장소 루트에서) python experiments/keyword_boost/keyword_boost.py <녹음 파일> <출력.txt> [boost] [키워드 ...]
  boost 를 0 으로 주거나 키워드를 주지 않으면 부스팅 없이 요청한다 (대조군).
예:   python experiments/keyword_boost/keyword_boost.py recordings/x.m4a out/boost7.txt 7 구인자 페르소나
      python experiments/keyword_boost/keyword_boost.py recordings/x.m4a out/control.txt 0

runs/ 를 건드리지 않고 매번 새로 업로드해 인식한다 (회당 과금). 결과는 인식 텍스트 한 파일.
토큰은 환경 변수 DAGLO_API_TOKEN. 다른 실험 폴더에 기대지 않도록 업로드·폴링 코드를 이 파일에 둔다.
"""

import json
import os
import sys
import time
from pathlib import Path

import requests

API_URL = "https://apis.daglo.ai/stt/v1/async/transcripts"
POLL_INTERVAL_SEC = 5
POLL_TIMEOUT_SEC = 60 * 60
ERROR_STATUSES = {"transcript_error", "file_error"}


def _headers() -> dict:
    token = os.environ.get("DAGLO_API_TOKEN")
    if not token:
        sys.exit("환경 변수 DAGLO_API_TOKEN 이 없습니다.")
    return {"Authorization": f"Bearer {token}"}


def wait_result(rid: str) -> dict:
    """끝날 때까지 폴링해서 응답 원본을 돌려준다 (루트 daglo.py 와 같은 방식)."""
    deadline = time.monotonic() + POLL_TIMEOUT_SEC
    last_status = None
    while time.monotonic() < deadline:
        res = requests.get(f"{API_URL}/{rid}", headers=_headers(), timeout=60)
        if not res.ok:
            sys.exit(f"결과 조회 실패: HTTP {res.status_code}\n{res.text}")
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


def transcribe(audio_path: Path, keywords: list[str], boost: int) -> str:
    stt_config = {"language": "ko-KR", "speakerDiarization": {"enable": True}}
    if keywords and boost > 0:
        stt_config["keywordBoost"] = {"enable": True, "keywords": keywords, "boost": boost}
    print(f"sttConfig: {json.dumps(stt_config, ensure_ascii=False)}")
    with audio_path.open("rb") as f:
        res = requests.post(
            API_URL, headers=_headers(), files={"file": (audio_path.name, f)},
            data={"sttConfig": json.dumps(stt_config)}, timeout=600,
        )
    if not res.ok:
        sys.exit(f"업로드 실패: HTTP {res.status_code}\n{res.text}")
    body = wait_result(res.json()["rid"])
    return "\n".join(r.get("transcript", "") for r in body.get("sttResults", []))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("사용법: python experiments/keyword_boost/keyword_boost.py <녹음 파일> <출력.txt> [boost] [키워드 ...]")
    audio, out = Path(sys.argv[1]), Path(sys.argv[2])
    boost = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    keywords = sys.argv[4:]
    text = transcribe(audio, keywords, boost)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"저장: {out}")

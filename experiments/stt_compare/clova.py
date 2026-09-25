"""네이버 CLOVA Speech 장문 인식 호출 (다글로와 인식률 비교용).

사용법: (저장소 루트에서) python experiments/stt_compare/clova.py <녹음 파일>
결과:   runs/<회의ID>/clova_response.json (응답 원본), runs/<회의ID>/clova_transcript.txt (텍스트만)

환경 변수:
  CLOVA_SPEECH_SECRET      CLOVA Speech 도메인 > 설정 > 연동 정보의 Secret Key
  CLOVA_SPEECH_INVOKE_URL  같은 곳의 Invoke URL (https://clovaspeech-gw.ncloud.com/external/v1/<id>/<key>)

회의 ID 는 daglo.py 와 같은 방식(녹음 파일 해시)이라 같은 runs/ 폴더에 결과가 나란히 쌓인다.
동기(sync) 방식으로 요청하므로 응답이 올 때까지 기다린다 (문서상 sync 는 2시간까지).
"""

import json
import os
import sys
import time
from pathlib import Path

import requests

from daglo import RUNS_DIR, meeting_id  # 같은 폴더의 daglo.py (실험 당시 스냅샷)


def _env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        sys.exit(f"환경 변수 {name} 이 없습니다.")
    return value


def recognize(audio_path: Path) -> dict:
    """녹음 파일을 multipart 로 올리고 인식 결과 JSON 을 돌려준다."""
    params = {
        "language": "ko-KR",
        "completion": "sync",
        "diarization": {"enable": True},
        "wordAlignment": True,
        "fullText": True,
    }
    url = _env("CLOVA_SPEECH_INVOKE_URL").rstrip("/") + "/recognizer/upload"
    headers = {"X-CLOVASPEECH-API-KEY": _env("CLOVA_SPEECH_SECRET")}
    with audio_path.open("rb") as f:
        res = requests.post(
            url,
            headers=headers,
            files={
                "media": (audio_path.name, f),
                "params": (None, json.dumps(params), "application/json"),
            },
            timeout=1800,
        )
    if not res.ok:
        sys.exit(f"인식 실패: HTTP {res.status_code}\n{res.text}")
    body = res.json()
    if body.get("result") != "COMPLETED":
        sys.exit(f"인식 실패: {json.dumps(body, ensure_ascii=False)[:500]}")
    return body


def transcribe(audio_path: Path) -> Path:
    run_dir = RUNS_DIR / meeting_id(audio_path)
    run_dir.mkdir(parents=True, exist_ok=True)
    response_file = run_dir / "clova_response.json"

    if response_file.exists():
        print(f"이미 결과가 있습니다: {response_file}")
        return run_dir

    print(f"업로드·인식 중 (동기): {audio_path.name}")
    started = time.monotonic()
    body = recognize(audio_path)
    print(f"인식 완료 ({time.monotonic() - started:.0f}초), 화자 {len(body.get('speakers', []))}명, "
          f"세그먼트 {len(body.get('segments', []))}개, confidence {body.get('confidence', 0):.3f}")

    response_file.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "clova_transcript.txt").write_text(body.get("text", ""), encoding="utf-8")
    return run_dir


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("사용법: (저장소 루트에서) python experiments/stt_compare/clova.py <녹음 파일>")
    path = Path(sys.argv[1])
    if not path.is_file():
        sys.exit(f"파일이 없습니다: {path}")
    print(f"저장 위치: {transcribe(path)}")

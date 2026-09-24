"""다글로 STT API 호출 (1단계: 음성 인식).

사용법: python daglo.py <녹음 파일>
결과:   runs/<회의ID>/stt_response.json (응답 원본), runs/<회의ID>/transcript.txt (텍스트만)

API 토큰은 환경 변수 DAGLO_API_TOKEN 에서만 읽는다.
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import requests

API_URL = "https://apis.daglo.ai/stt/v1/async/transcripts"
RUNS_DIR = Path("runs")
POLL_INTERVAL_SEC = 5
POLL_TIMEOUT_SEC = 60 * 60
ERROR_STATUSES = {"transcript_error", "file_error"}


def meeting_id(audio_path: Path) -> str:
    """회의 ID = 녹음 파일의 해시."""
    h = hashlib.sha256()
    with audio_path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _headers() -> dict:
    token = os.environ.get("DAGLO_API_TOKEN")
    if not token:
        sys.exit("환경 변수 DAGLO_API_TOKEN 이 없습니다.")
    return {"Authorization": f"Bearer {token}"}


# 다글로 API에 application/url, multipart/data-form 두 가지 방식이 있는데 나는 멀티파트 선택(파일 직접 올리려고)
# request_transcript가 하는 건 파일 읽고, 세팅 값과 함께 다글로 API에 요청을 보내고 rid를 받는 것
def request_transcript(audio_path: Path) -> str:
    """녹음 파일을 multipart 로 직접 올리고 rid 를 받는다."""
    stt_config = {"language": "ko-KR", "speakerDiarization": {"enable": True}}
    with audio_path.open("rb") as f:
        res = requests.post(
            API_URL,
            headers=_headers(),
            files={"file": (audio_path.name, f)},
            data={"sttConfig": json.dumps(stt_config)},
            timeout=600, # 제한 시간 600초 (10분 안에 응답 없으면 오류)
        )
    if not res.ok:
        sys.exit(f"업로드 실패: HTTP {res.status_code}\n{res.text}")
    return res.json()["rid"]


# time.monotonic()은 컴퓨터가 켜진 뒤 흐른 초를 소수로 돌려주는 함수로, 두 번 찍어서 차이를 구하는 용도로 사용한다.
def wait_result(rid: str) -> dict:
    """끝날 때까지 폴링해서 응답 원본을 돌려준다."""
    deadline = time.monotonic() + POLL_TIMEOUT_SEC
    last_status = None
    while time.monotonic() < deadline:
        res = requests.get(f"{API_URL}/{rid}", headers=_headers(), timeout=60) # 이 rid로 보냈던 요청 어떻게 됐는지 get
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
    sys.exit(f"시간 초과: rid={rid} (같은 명령으로 다시 실행하면 이어서 조회합니다)")


# 위 함수들 조립해서 실제로 회의록 원본 뽑는 함수
def transcribe(audio_path: Path) -> Path:
    run_dir = RUNS_DIR / meeting_id(audio_path)
    run_dir.mkdir(parents=True, exist_ok=True)
    response_file = run_dir / "stt_response.json"
    rid_file = run_dir / "stt_rid.txt"

    # 결과가 이미 있으면 바로 결과 돌려줌 (멱등성 보장)
    if response_file.exists():
        print(f"이미 결과가 있습니다: {response_file}")
        return run_dir

    # rid를 남겨둬서 중복 업로드를 피한다. -> 같은 파일 업로드로 크레딧 낭비 방지 (멱등성 보장)
    if rid_file.exists():
        rid = rid_file.read_text(encoding="utf-8").strip()
        print(f"기존 요청을 이어서 조회합니다: rid={rid}")
    else:
        print(f"업로드 중: {audio_path.name}")
        rid = request_transcript(audio_path)
        rid_file.write_text(rid, encoding="utf-8")
        print(f"요청 완료: rid={rid}")

    started = time.monotonic()
    body = wait_result(rid)
    print(f"변환 완료 ({time.monotonic() - started:.0f}초)")

    response_file.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    text = "\n".join(r.get("transcript", "") for r in body.get("sttResults", []))
    (run_dir / "transcript.txt").write_text(text, encoding="utf-8")
    return run_dir
# 이 함수 약점
# 첫 번째 실행에서 stt_rid.txt만 남기고 다글로쪽 작업이 실패하면, 다시 돌려도 계속 실패한 rid만 조회함.
# 이때는 stt_rid.txt를 지워야 재업로드가 되는데, 이건 나중에 보강할 예정


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("사용법: python daglo.py <녹음 파일>")
    path = Path(sys.argv[1])
    if not path.is_file():
        sys.exit(f"파일이 없습니다: {path}")
    out = transcribe(path)
    print(f"저장 위치: {out}")

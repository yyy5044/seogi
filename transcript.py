"""다글로 응답을 발언 단위 원문으로 만든다 (2단계: 원문 만들기).

사용법: python transcript.py runs/<회의ID>   (또는 회의ID 만)
입력:   runs/<회의ID>/stt_response.json   (1단계 daglo.py 결과)
출력:   runs/<회의ID>/transcript.md       (발언 번호 / 시각 / 화자 / 내용 표)
        runs/<회의ID>/utterances.json     (같은 내용, 뒤 단계가 읽기 위한 원본)

외부 API 는 부르지 않는다. 화자가 바뀌는 지점에서 발언을 끊는다.
다글로의 segmentId 는 문서에 정의가 없어 쓰지 않는다.
"""

import json
import sys
from pathlib import Path

RUNS_DIR = Path("runs")

# 시작 시간 구하는 함수
def _start_seconds(word: dict) -> float:
    """다글로 시각 {seconds: "12", nanos: 340000000} → 12.34 (seconds 는 문자열로 온다)."""
    t = word["startTime"]
    return int(t["seconds"]) + t.get("nanos", 0) / 1e9


# 초를 hh:mm:ss로 바꿔주는 함수 (소수점 아래는 버림)
def format_time(seconds: float) -> str:
    """초 → mm:ss. 한 시간이 넘으면 h:mm:ss."""
    s = int(seconds)
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"


def group_utterances(words: list[dict]) -> list[dict]:
    """단어 목록 → 발언 목록. 화자가 바뀔 때마다 발언을 끊는다.

    발언: {"no": 발언 번호(1부터), "start": 첫 단어 시각(초), "speaker": "화자1", "text": 내용}
    단어 앞에 다글로가 붙여 준 공백이 있으므로 구분자 없이 이어 붙이고 양끝만 다듬는다.
    """
    utterances: list[dict] = [] # 발언 목록(이름표 붙은 주머니들) <- 빈 목록
    current: dict | None = None # 지금 열려 있는 주머니 <- 없음

    for w in words:
        speaker = str(w.get("speaker", "?")) # speaker가 없으면 "?"로 표시
        if current is None or current["speaker_id"] != speaker:
            if current is not None: # 만약 지금 열려 있는 주머니(current)가 있으면
                utterances.append(current) # 발언목록에 현재 주머니를 봉해 넣는다
            current = {"speaker_id": speaker, "start": _start_seconds(w), "parts": []} # 현재주머니 <- 새 주머니
        current["parts"].append(w.get("word", "")) # 현재주머니의 parts에 발언 조각 append

    if current is not None: # 루프 끝난 뒤 마지막 주머니 처리
        utterances.append(current) 

    return [ # 파이선 컴프리헨션 문법으로 utterances를 아래 구조로 바꿔 리턴
        {
            "no": i,
            "start": u["start"],
            "speaker": f"화자{u['speaker_id']}",
            "text": "".join(u["parts"]).strip(),
        }
        for i, u in enumerate(utterances, start=1)
    ]


def write_transcript(utterances: list[dict], run_dir: Path) -> Path:
    """발언 목록을 transcript.md(표)와 utterances.json 으로 저장하고 md 경로를 돌려준다."""
    lines = ["| 번호 | 시각 | 화자 | 내용 |", "|---|---|---|---|"]
    for u in utterances:
        text = u["text"].replace("|", "\\|") # 표 칸 구분자와 충돌 방지
        lines.append(f"| {u['no']} | {format_time(u['start'])} | {u['speaker']} | {text} |")

    md_path = run_dir / "transcript.md" # 경로에 transcript.md 만들고
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8") # lines 쓰기
    (run_dir / "utterances.json").write_text( # group_utterances에서 반환한 리스트를 그대로 utterances.json에 쓰기
        json.dumps(utterances, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return md_path


def build(run_dir: Path) -> list[dict]:
    """runs/<회의ID>/stt_response.json → 원문 파일. 발언 목록을 돌려준다."""
    response_file = run_dir / "stt_response.json"
    if not response_file.exists():
        sys.exit(f"1단계 결과가 없습니다: {response_file} (daglo.py 를 먼저 실행하세요)")

    body = json.loads(response_file.read_text(encoding="utf-8")) # loads(문자열 -> 딕셔너리)는 dumps의 반대 
    words = [w for r in body.get("sttResults", []) for w in r.get("words", [])]
    utterances = group_utterances(words)
    md_path = write_transcript(utterances, run_dir)
    print(f"단어 {len(words)}개 → 발언 {len(utterances)}개, 저장: {md_path}")
    return utterances


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("사용법: python transcript.py runs/<회의ID>")
    arg = Path(sys.argv[1])
    run_dir = arg if arg.is_dir() else RUNS_DIR / sys.argv[1]
    if not run_dir.is_dir():
        sys.exit(f"폴더가 없습니다: {run_dir}")
    build(run_dir)

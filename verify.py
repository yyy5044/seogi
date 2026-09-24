"""근거 검증 (4단계).

사용법: python verify.py runs/<회의ID>   (또는 회의ID 만)
입력:   runs/<회의ID>/extraction.json   (3단계 결과. 결정사항·할 일에 근거 발언 번호 evidence)
        runs/<회의ID>/utterances.json   (2단계 결과. 발언 번호 no, 시각 start, 화자, 내용)
출력:   runs/<회의ID>/minutes.md        (정리본. 근거를 번호 대신 발언 시각으로 표시)
        runs/<회의ID>/excluded.json     (정리본에서 뺀 항목과 이유)

LLM 이 지어낸 항목을 거르는 단계. 결정사항과 할 일의 근거 번호가 원문(utterances.json)에
실제로 있는지 코드로 확인한다. 번호가 하나라도 원문에 없거나 근거가 비어 있으면 그 항목은
통째로 정리본에서 빼고 제외 목록에 남긴다. 제목·요약·대화 주제는 근거가 없는 항목이라 그대로 통과한다.
LLM 은 부르지 않는다.
"""

import json
import sys
import time
from pathlib import Path

from transcript import format_time

RUNS_DIR = Path("runs")

# 근거 검증 대상. (extraction.json 의 키, 사람이 읽는 이름)
_CHECKED = [("decisions", "결정사항"), ("todos", "할 일")]


def check_item(item: dict, valid_nos: set[int]) -> str | None:
    """항목 하나의 근거 번호를 검사한다. 문제가 없으면 None, 있으면 제외 이유를 돌려준다."""
    evidence = item.get("evidence", [])
    if not evidence:
        return "근거 없음"
    missing = sorted(set(evidence) - valid_nos)
    if missing:
        return f"원문에 없는 번호: {missing}"
    return None


def verify(data: dict, utterances: list[dict]) -> tuple[dict, list[dict]]:
    """추출 결과를 원문과 대조해 (통과한 결과, 제외 목록) 을 돌려준다.

    통과한 결과는 extraction.json 과 같은 구조에서 문제 있는 항목만 빠진 것이다.
    제외 목록의 항목은 {"kind": "결정사항"|"할 일", "item": 원래 항목, "reason": 이유}.
    """
    valid_nos = {u["no"] for u in utterances}
    kept = dict(data)
    excluded = []
    for key, kind in _CHECKED:
        kept[key] = []
        for item in data.get(key, []):
            reason = check_item(item, valid_nos)
            if reason is None:
                kept[key].append(item)
            else:
                excluded.append({"kind": kind, "item": item, "reason": reason})
    return kept, excluded


def render_minutes(data: dict, utterances: list[dict]) -> str:
    """통과한 결과 → 정리본 마크다운. 근거는 발언 번호 대신 그 발언의 시각으로 적는다."""
    start_by_no = {u["no"]: u["start"] for u in utterances}

    def evidence_times(nos: list[int]) -> str:
        return ", ".join(format_time(start_by_no[no]) for no in sorted(set(nos)))

    out = [f"# {data['title']}", "", "## 요약", "", data["summary"] or "(없음)"]

    out += ["", "## 대화 주제", ""]
    out += [f"- {t}" for t in data["topics"]] or ["- (없음)"]

    out += ["", "## 결정사항", ""]
    if not data["decisions"]:
        out.append("- (없음)")
    for i, d in enumerate(data["decisions"], start=1):
        out.append(f"{i}. {d['text']} (근거: {evidence_times(d['evidence'])})")

    out += ["", "## 할 일", ""]
    if not data["todos"]:
        out.append("- (없음)")
    for i, t in enumerate(data["todos"], start=1):
        meta = " / ".join(x for x in (t.get("owner", ""), t.get("due", "")) if x)
        head = f"{i}. {t['text']}" + (f" ({meta})" if meta else "")
        out.append(f"{head} (근거: {evidence_times(t['evidence'])})")

    return "\n".join(out) + "\n"


def run(run_dir: Path) -> tuple[dict, list[dict]]:
    """runs/<회의ID>/extraction.json → minutes.md, excluded.json. (통과한 결과, 제외 목록) 을 돌려준다."""
    extraction_file = run_dir / "extraction.json"
    utterances_file = run_dir / "utterances.json"
    if not extraction_file.exists() or not utterances_file.exists():
        sys.exit(f"3단계 결과가 없습니다: {run_dir} (llm.py 를 먼저 실행하세요)")

    started = time.monotonic()
    data = json.loads(extraction_file.read_text(encoding="utf-8"))
    utterances = json.loads(utterances_file.read_text(encoding="utf-8"))

    kept, excluded = verify(data, utterances)

    minutes_file = run_dir / "minutes.md"
    minutes_file.write_text(render_minutes(kept, utterances), encoding="utf-8")
    (run_dir / "excluded.json").write_text(
        json.dumps(excluded, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    elapsed = time.monotonic() - started
    total = sum(len(data.get(k, [])) for k, _ in _CHECKED)
    print(
        f"완료 ({elapsed:.2f}초): 검사 {total}개 → 통과 {total - len(excluded)}개, 제외 {len(excluded)}개 "
        f"(결정사항 {len(kept['decisions'])}개, 할 일 {len(kept['todos'])}개)"
    )
    for e in excluded:
        print(f"  제외 [{e['kind']}] {e['item']['text']} / {e['reason']}")
    print(f"저장: {minutes_file}, 제외 목록: {run_dir / 'excluded.json'}")
    return kept, excluded


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("사용법: python verify.py runs/<회의ID>")
    arg = Path(sys.argv[1])
    run_dir = arg if arg.is_dir() else RUNS_DIR / sys.argv[1]
    if not run_dir.is_dir():
        sys.exit(f"폴더가 없습니다: {run_dir}")
    run(run_dir)

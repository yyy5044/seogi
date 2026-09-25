"""노션 API 호출 (5단계: 노션 기록).

사용법: python notion.py runs/<회의ID>   (또는 회의ID 만)
입력:   runs/<회의ID>/recording.json    (1단계. 녹음 파일 이름과 수정 시각 → 회의일)
        runs/<회의ID>/verified.json     (4단계. 근거 검증을 통과한 제목·요약·대화 주제·결정사항·할 일)
        runs/<회의ID>/excluded.json     (4단계. 정리본에서 뺀 항목과 이유)
        runs/<회의ID>/utterances.json   (2단계. 원문 표와 근거 시각에 쓴다)
출력:   회의록 DB 에 페이지 1개. 본문은 요약 → 대화 주제 → 결정사항 → 할 일 → 제외 목록,
        맨 아래 하위 페이지 "원문" 에 발언 표. 만든 페이지 주소는 runs/<회의ID>/notion_page.json 에 남긴다.

환경 변수: NOTION_API_KEY (내부 통합 토큰), NOTION_DATABASE_ID (회의록 DB 주소의 32자리 ID).
같은 회의 ID 가 DB 에 이미 있으면 페이지를 다시 만들지 않는다. 지정한 DB 밖은 건드리지 않는다.
레코드 제목은 회의일(YYYY-MM-DD). 같은 날 회의가 이미 n개 있으면 "YYYY-MM-DD (n)".
"""

import json
import os
import sys
import time
from pathlib import Path

import requests

from verify import evidence_times
from transcript import format_time

API_BASE = "https://api.notion.com/v1"
API_VERSION = "2025-09-03"
RUNS_DIR = Path("runs")
STATUS_NEW = "자동 생성(미검수)"
MAX_TEXT = 2000        # 텍스트 조각 하나의 글자 수 상한 (노션 제한)
MAX_CHILDREN = 100     # 요청 하나에 넣을 수 있는 블록 수 상한 (노션 제한)
TRANSCRIPT_PAGE_TITLE = "원문"


# ---------- API 호출 ----------

def _headers() -> dict:
    token = os.environ.get("NOTION_API_KEY")
    if not token:
        sys.exit("환경 변수 NOTION_API_KEY 가 없습니다.")
    return {"Authorization": f"Bearer {token}", "Notion-Version": API_VERSION, "Content-Type": "application/json"}


def _request(method: str, path: str, body: dict | None = None) -> dict:
    """노션 API 를 한 번 부른다. 실패하면 응답 본문을 보여 주고 종료한다. 429 는 잠깐 기다렸다 다시 시도."""
    for attempt in range(5):
        res = requests.request(method, f"{API_BASE}{path}", headers=_headers(), json=body, timeout=60)
        if res.status_code == 429:
            time.sleep(float(res.headers.get("Retry-After", "1")))
            continue
        if not res.ok:
            sys.exit(f"노션 API 실패: {method} {path} → HTTP {res.status_code}\n{res.text}")
        return res.json()
    sys.exit(f"노션 API 실패: {method} {path} → 요청이 너무 많아 {attempt + 1}번 시도 후 포기")


def data_source_id(database_id: str) -> str:
    """DB ID → 데이터 소스 ID. 페이지 생성과 조회는 데이터 소스 기준으로 한다 (API 2025-09-03)."""
    db = _request("GET", f"/databases/{database_id}")
    sources = db.get("data_sources", [])
    if not sources:
        sys.exit(f"DB 에 데이터 소스가 없습니다: {database_id}")
    return sources[0]["id"]


def query_all(ds_id: str, filter_: dict) -> list[dict]:
    """데이터 소스를 조건으로 조회해 페이지 목록 전부를 돌려준다 (페이지 넘김 처리)."""
    pages, cursor = [], None
    while True:
        body = {"filter": filter_}
        if cursor:
            body["start_cursor"] = cursor
        res = _request("POST", f"/data_sources/{ds_id}/query", body)
        pages += res.get("results", [])
        if not res.get("has_more"):
            return pages
        cursor = res.get("next_cursor")


def find_page(ds_id: str, meeting_id: str) -> dict | None:
    """같은 회의 ID 로 이미 만든 페이지가 있으면 돌려준다 (중복 방지)."""
    pages = query_all(ds_id, {"property": "회의 ID", "rich_text": {"equals": meeting_id}})
    return pages[0] if pages else None


def count_same_day(ds_id: str, date: str) -> int:
    """같은 회의일로 이미 만든 페이지 수. 제목 뒤에 붙일 번호를 정할 때 쓴다."""
    return len(query_all(ds_id, {"property": "회의일", "date": {"equals": date}}))


def create_page(parent: dict, properties: dict, children: list[dict]) -> dict:
    return _request("POST", "/pages", {"parent": parent, "properties": properties, "children": children})


def append_children(block_id: str, blocks: list[dict]) -> None:
    """블록 목록을 100개씩 나눠 덧붙인다."""
    for i in range(0, len(blocks), MAX_CHILDREN):
        _request("PATCH", f"/blocks/{block_id}/children", {"children": blocks[i : i + MAX_CHILDREN]})


# ---------- 내용 → 노션 블록 ----------

def rich_text(text: str) -> list[dict]:
    """문자열 → 노션 rich_text 목록. 2000자 제한에 맞춰 조각낸다. 빈 문자열은 빈 목록."""
    return [{"type": "text", "text": {"content": text[i : i + MAX_TEXT]}} for i in range(0, len(text), MAX_TEXT)]


def _block(kind: str, text: str, **extra) -> dict:
    return {"object": "block", "type": kind, kind: {"rich_text": rich_text(text), **extra}}


def heading(text: str) -> dict:
    return _block("heading_2", text)


def paragraph(text: str) -> dict:
    return _block("paragraph", text)


def bullet(text: str) -> dict:
    return _block("bulleted_list_item", text)


def numbered(text: str) -> dict:
    return _block("numbered_list_item", text)


def page_title(date: str, same_day_count: int) -> str:
    """회의일 → 레코드 제목. 같은 날 회의가 이미 있으면 뒤에 (n)."""
    return date if same_day_count == 0 else f"{date} ({same_day_count})"


def page_properties(title: str, date: str, meeting_id: str, recording_file: str) -> dict:
    return {
        "회의": {"title": rich_text(title)},
        "회의일": {"date": {"start": date}},
        "상태": {"select": {"name": STATUS_NEW}},
        "회의 ID": {"rich_text": rich_text(meeting_id)},
        "녹음 파일": {"rich_text": rich_text(recording_file)},
    }


def body_blocks(verified: dict, excluded: list[dict], utterances: list[dict]) -> list[dict]:
    """정리본 + 제외 목록 → 페이지 본문 블록. 순서는 명세서대로 요약 → 대화 주제 → 결정사항 → 할 일 → 제외 목록."""
    out = [heading("요약"), paragraph(verified["summary"] or "(없음)")]

    out.append(heading("대화 주제"))
    out += [bullet(t) for t in verified["topics"]] or [bullet("(없음)")]

    out.append(heading("결정사항"))
    out += [
        numbered(f"{d['text']} (근거: {evidence_times(d['evidence'], utterances)})") for d in verified["decisions"]
    ] or [bullet("(없음)")]

    out.append(heading("할 일"))
    for t in verified["todos"]:
        meta = " / ".join(x for x in (t.get("owner", ""), t.get("due", "")) if x)
        head = t["text"] + (f" ({meta})" if meta else "")
        out.append(numbered(f"{head} (근거: {evidence_times(t['evidence'], utterances)})"))
    if not verified["todos"]:
        out.append(bullet("(없음)"))

    out.append(heading("제외 목록"))
    out += [bullet(f"[{e['kind']}] {e['item']['text']} / {e['reason']}") for e in excluded] or [bullet("(없음)")]

    out.append(heading("원문"))
    out.append(paragraph(f"아래 하위 페이지 '{TRANSCRIPT_PAGE_TITLE}' 에 발언 {len(utterances)}개를 표로 보관한다."))
    return out


def transcript_tables(utterances: list[dict]) -> list[dict]:
    """발언 목록 → 표 블록 목록. 표 하나에 행을 100개까지만 넣을 수 있어 99개씩 끊어 여러 표로 만든다."""
    header = {"type": "table_row", "table_row": {"cells": [rich_text(h) for h in ("번호", "시각", "화자", "내용")]}}
    rows = [
        {"type": "table_row", "table_row": {"cells": [
            rich_text(str(u["no"])), rich_text(format_time(u["start"])), rich_text(u["speaker"]), rich_text(u["text"]),
        ]}}
        for u in utterances
    ]
    per_table = MAX_CHILDREN - 1
    tables = []
    for i in range(0, max(len(rows), 1), per_table):
        tables.append({
            "object": "block", "type": "table",
            "table": {"table_width": 4, "has_column_header": True, "has_row_header": False,
                      "children": [header] + rows[i : i + per_table]},
        })
    return tables


# ---------- 조립 ----------

def run(run_dir: Path) -> str:
    """runs/<회의ID>/ 의 4단계 결과 → 노션 페이지. 페이지 주소를 돌려준다."""
    needed = {name: run_dir / name for name in ("recording.json", "verified.json", "excluded.json", "utterances.json")}
    missing = [name for name, p in needed.items() if not p.exists()]
    if missing:
        sys.exit(f"입력 파일이 없습니다: {run_dir} / {', '.join(missing)} (앞 단계를 먼저 실행하세요)")
    load = lambda name: json.loads(needed[name].read_text(encoding="utf-8"))
    recording, verified, excluded, utterances = load("recording.json"), load("verified.json"), load("excluded.json"), load("utterances.json")

    database_id = os.environ.get("NOTION_DATABASE_ID")
    if not database_id:
        sys.exit("환경 변수 NOTION_DATABASE_ID 가 없습니다.")
    meeting_id = run_dir.name
    date = recording["modified"][:10]

    started = time.monotonic()
    ds_id = data_source_id(database_id)

    existing = find_page(ds_id, meeting_id)
    if existing:
        print(f"이미 페이지가 있습니다 (회의 ID {meeting_id}): {existing['url']}")
        return existing["url"]

    title = page_title(date, count_same_day(ds_id, date))
    body = body_blocks(verified, excluded, utterances)
    page = create_page(
        {"type": "data_source_id", "data_source_id": ds_id},
        page_properties(title, date, meeting_id, recording["file"]),
        body[:MAX_CHILDREN],
    )
    append_children(page["id"], body[MAX_CHILDREN:])

    tables = transcript_tables(utterances)
    sub = create_page(
        {"type": "page_id", "page_id": page["id"]},
        {"title": {"title": rich_text(TRANSCRIPT_PAGE_TITLE)}},
        tables[:1],
    )
    append_children(sub["id"], tables[1:])

    (run_dir / "notion_page.json").write_text(
        json.dumps({"url": page["url"], "id": page["id"], "title": title}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"완료 ({time.monotonic() - started:.0f}초): '{title}' 결정사항 {len(verified['decisions'])}개, "
        f"할 일 {len(verified['todos'])}개, 제외 {len(excluded)}개, 원문 발언 {len(utterances)}개"
    )
    print(f"페이지: {page['url']}")
    return page["url"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("사용법: python notion.py runs/<회의ID>")
    arg = Path(sys.argv[1])
    run_dir = arg if arg.is_dir() else RUNS_DIR / sys.argv[1]
    if not run_dir.is_dir():
        sys.exit(f"폴더가 없습니다: {run_dir}")
    run(run_dir)

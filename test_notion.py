"""5단계(notion.py) 테스트. 실행: python -m unittest test_notion -v

노션 API 는 부르지 않는다. _request 를 가짜로 바꿔 블록 만들기, 제목 번호, 중복 방지, 요청 순서를 확인한다.
표본은 실제 회의가 아니라 지어낸 발언이다.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import notion


def utt(no: int, start: float, speaker: str, text: str) -> dict:
    return {"no": no, "start": start, "speaker": speaker, "text": text}


UTTERANCES = [
    utt(1, 0.0, "화자1", "다음 주에 배포하죠"),
    utt(2, 4.5, "화자2", "네 좋습니다"),
    utt(3, 70.0, "화자1", "제가 문서를 정리할게요"),
]

VERIFIED = {
    "title": "배포 일정 회의",
    "summary": "배포 시점을 정하고 문서 정리 담당을 나눴다.",
    "topics": ["배포 시점", "문서 정리"],
    "decisions": [{"text": "다음 주에 배포한다.", "evidence": [2, 1]}],
    "todos": [{"text": "문서를 정리한다.", "owner": "화자1", "due": "", "evidence": [3]}],
}
EXCLUDED = [{"kind": "결정사항", "item": {"text": "예산을 늘린다.", "evidence": [99]}, "reason": "원문에 없는 번호: [99]"}]
RECORDING = {"file": "회의.m4a", "modified": "2026-09-21T13:05:00"}


def texts(block: dict) -> str:
    kind = block["type"]
    return "".join(t["text"]["content"] for t in block[kind]["rich_text"])


class RichTextTest(unittest.TestCase):
    def test_2000자_넘으면_조각낸다(self):
        parts = notion.rich_text("가" * 4500)
        self.assertEqual([len(p["text"]["content"]) for p in parts], [2000, 2000, 500])

    def test_빈_문자열은_빈_목록(self):
        self.assertEqual(notion.rich_text(""), [])


class PageTitleTest(unittest.TestCase):
    def test_같은_날_첫_회의는_일자만(self):
        self.assertEqual(notion.page_title("2026-09-21", 0), "2026-09-21")

    def test_같은_날_두_번째부터_번호를_붙인다(self):
        self.assertEqual(notion.page_title("2026-09-21", 1), "2026-09-21 (1)")
        self.assertEqual(notion.page_title("2026-09-21", 2), "2026-09-21 (2)")


class PagePropertiesTest(unittest.TestCase):
    def test_속성_다섯_개를_채운다(self):
        props = notion.page_properties("2026-09-21", "2026-09-21", "abc123", "회의.m4a")
        self.assertEqual(props["회의"]["title"][0]["text"]["content"], "2026-09-21")
        self.assertEqual(props["회의일"]["date"]["start"], "2026-09-21")
        self.assertEqual(props["상태"]["select"]["name"], "자동 생성(미검수)")
        self.assertEqual(props["회의 ID"]["rich_text"][0]["text"]["content"], "abc123")
        self.assertEqual(props["녹음 파일"]["rich_text"][0]["text"]["content"], "회의.m4a")


class BodyBlocksTest(unittest.TestCase):
    def test_순서와_근거_시각(self):
        blocks = notion.body_blocks(VERIFIED, EXCLUDED, UTTERANCES)
        headings = [texts(b) for b in blocks if b["type"] == "heading_2"]
        self.assertEqual(headings, ["요약", "대화 주제", "결정사항", "할 일", "제외 목록", "원문"])
        lines = [texts(b) for b in blocks]
        self.assertIn("배포 시점을 정하고 문서 정리 담당을 나눴다.", lines)
        self.assertIn("다음 주에 배포한다. (근거: 00:00, 00:04)", lines)
        self.assertIn("문서를 정리한다. (화자1) (근거: 01:10)", lines)
        self.assertIn("[결정사항] 예산을 늘린다. / 원문에 없는 번호: [99]", lines)

    def test_빈_결과에서_죽지_않는다(self):
        empty = {"title": "", "summary": "", "topics": [], "decisions": [], "todos": []}
        lines = [texts(b) for b in notion.body_blocks(empty, [], [])]
        self.assertEqual(lines.count("(없음)"), 5)


class TranscriptTablesTest(unittest.TestCase):
    def test_표_하나에_머리글과_발언_행(self):
        tables = notion.transcript_tables(UTTERANCES)
        self.assertEqual(len(tables), 1)
        rows = tables[0]["table"]["children"]
        self.assertEqual(len(rows), 4)
        first = rows[1]["table_row"]["cells"]
        self.assertEqual([c[0]["text"]["content"] for c in first], ["1", "00:00", "화자1", "다음 주에 배포하죠"])

    def test_행이_많으면_표를_나눈다(self):
        many = [utt(i, float(i), "화자1", "말") for i in range(1, 251)]
        tables = notion.transcript_tables(many)
        self.assertEqual([len(t["table"]["children"]) for t in tables], [100, 100, 53])  # 99+99+52 행 + 머리글

    def test_발언이_없어도_머리글만_있는_표_하나(self):
        tables = notion.transcript_tables([])
        self.assertEqual(len(tables[0]["table"]["children"]), 1)


class FakeApi:
    """_request 대역. 부른 순서를 기록하고 정해진 응답을 돌려준다."""

    def __init__(self, existing: list | None = None, same_day: int = 0):
        self.calls = []
        self.existing = existing or []
        self.same_day = same_day

    def __call__(self, method: str, path: str, body: dict | None = None) -> dict:
        self.calls.append((method, path, body))
        if path.startswith("/databases/"):
            return {"data_sources": [{"id": "ds-1", "name": "회의록"}]}
        if path.endswith("/query"):
            prop = body["filter"]["property"]
            if prop == "회의 ID":
                return {"results": self.existing, "has_more": False}
            return {"results": [{}] * self.same_day, "has_more": False}
        if path == "/pages":
            n = sum(1 for m, p, _ in self.calls if p == "/pages")
            return {"id": f"page-{n}", "url": f"https://notion.so/page-{n}"}
        if path.endswith("/children"):
            return {}
        raise AssertionError(f"예상 밖 호출: {method} {path}")


class RunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()) / "abc123"
        self.tmp.mkdir()
        for name, data in (("recording.json", RECORDING), ("verified.json", VERIFIED),
                           ("excluded.json", EXCLUDED), ("utterances.json", UTTERANCES)):
            (self.tmp / name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        self.env = mock.patch.dict("os.environ", {"NOTION_DATABASE_ID": "db-1"})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_페이지와_원문_하위_페이지를_만든다(self):
        api = FakeApi()
        with mock.patch.object(notion, "_request", api):
            url = notion.run(self.tmp)
        self.assertEqual(url, "https://notion.so/page-1")
        page_calls = [c for c in api.calls if c[1] == "/pages"]
        self.assertEqual(len(page_calls), 2)
        main_body = page_calls[0][2]
        self.assertEqual(main_body["parent"], {"type": "data_source_id", "data_source_id": "ds-1"})
        self.assertEqual(main_body["properties"]["회의 ID"]["rich_text"][0]["text"]["content"], "abc123")
        self.assertEqual(main_body["properties"]["회의"]["title"][0]["text"]["content"], "2026-09-21")
        sub_body = page_calls[1][2]
        self.assertEqual(sub_body["parent"], {"type": "page_id", "page_id": "page-1"})
        self.assertEqual(sub_body["children"][0]["type"], "table")
        saved = json.loads((self.tmp / "notion_page.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["url"], url)

    def test_같은_회의_ID_가_있으면_만들지_않는다(self):
        api = FakeApi(existing=[{"id": "old", "url": "https://notion.so/old"}])
        with mock.patch.object(notion, "_request", api):
            url = notion.run(self.tmp)
        self.assertEqual(url, "https://notion.so/old")
        self.assertFalse(any(c[1] == "/pages" for c in api.calls))
        self.assertFalse((self.tmp / "notion_page.json").exists())

    def test_같은_날_회의가_있으면_제목에_번호(self):
        api = FakeApi(same_day=2)
        with mock.patch.object(notion, "_request", api):
            notion.run(self.tmp)
        main_body = next(c[2] for c in api.calls if c[1] == "/pages")
        self.assertEqual(main_body["properties"]["회의"]["title"][0]["text"]["content"], "2026-09-21 (2)")

    def test_입력_파일이_없으면_종료한다(self):
        (self.tmp / "verified.json").unlink()
        with self.assertRaises(SystemExit):
            notion.run(self.tmp)

    def test_DB_ID_환경_변수가_없으면_종료한다(self):
        with mock.patch.dict("os.environ", {"NOTION_DATABASE_ID": ""}):
            with self.assertRaises(SystemExit):
                notion.run(self.tmp)


if __name__ == "__main__":
    unittest.main()

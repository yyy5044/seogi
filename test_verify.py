"""4단계(verify.py) 테스트. 실행: python -m unittest test_verify -v

명세서 완료 기준: 가짜 근거 번호를 단 항목이 제외된다 / 정상 항목은 통과한다 / 빈 입력에서 죽지 않는다.
표본은 실제 회의가 아니라 지어낸 발언이다.
"""

import json
import tempfile
import unittest
from pathlib import Path

import verify


def utt(no: int, start: float, speaker: str, text: str) -> dict:
    return {"no": no, "start": start, "speaker": speaker, "text": text}


UTTERANCES = [
    utt(1, 0.0, "화자1", "다음 주에 배포하죠"),
    utt(2, 4.5, "화자2", "네 좋습니다"),
    utt(3, 70.0, "화자1", "제가 문서를 정리할게요"),
]

GOOD_DECISION = {"text": "다음 주에 배포한다.", "evidence": [2, 1]}
FAKE_DECISION = {"text": "예산을 두 배로 늘린다.", "evidence": [1, 99]}
NO_EVIDENCE_DECISION = {"text": "회의를 매주 연다.", "evidence": []}
GOOD_TODO = {"text": "문서를 정리한다.", "owner": "화자1", "due": "", "evidence": [3]}
FAKE_TODO = {"text": "서버를 산다.", "owner": "화자2", "due": "내일", "evidence": [42]}

DATA = {
    "title": "배포 일정 회의",
    "summary": "배포 시점을 정하고 문서 정리 담당을 나눴다.",
    "topics": ["배포 시점", "문서 정리"],
    "decisions": [GOOD_DECISION, FAKE_DECISION, NO_EVIDENCE_DECISION],
    "todos": [GOOD_TODO, FAKE_TODO],
}


class CheckItemTest(unittest.TestCase):
    def test_정상_항목은_문제_없음(self):
        self.assertIsNone(verify.check_item(GOOD_DECISION, {1, 2, 3}))

    def test_원문에_없는_번호가_섞이면_그_번호를_이유로_돌려준다(self):
        self.assertEqual(verify.check_item(FAKE_DECISION, {1, 2, 3}), "원문에 없는 번호: [99]")

    def test_근거가_비면_제외(self):
        self.assertEqual(verify.check_item(NO_EVIDENCE_DECISION, {1, 2, 3}), "근거 없음")


class VerifyTest(unittest.TestCase):
    def test_가짜_근거_번호를_단_항목이_제외된다(self):
        kept, excluded = verify.verify(DATA, UTTERANCES)
        self.assertNotIn(FAKE_DECISION, kept["decisions"])
        self.assertNotIn(NO_EVIDENCE_DECISION, kept["decisions"])
        self.assertNotIn(FAKE_TODO, kept["todos"])
        self.assertEqual(len(excluded), 3)
        self.assertEqual(
            [(e["kind"], e["reason"]) for e in excluded],
            [("결정사항", "원문에 없는 번호: [99]"), ("결정사항", "근거 없음"), ("할 일", "원문에 없는 번호: [42]")],
        )
        self.assertEqual(excluded[0]["item"], FAKE_DECISION)

    def test_정상_항목은_통과한다(self):
        kept, _ = verify.verify(DATA, UTTERANCES)
        self.assertEqual(kept["decisions"], [GOOD_DECISION])
        self.assertEqual(kept["todos"], [GOOD_TODO])

    def test_근거가_없는_항목은_그대로_통과한다(self):
        kept, _ = verify.verify(DATA, UTTERANCES)
        self.assertEqual(kept["title"], DATA["title"])
        self.assertEqual(kept["summary"], DATA["summary"])
        self.assertEqual(kept["topics"], DATA["topics"])

    def test_원본을_고치지_않는다(self):
        verify.verify(DATA, UTTERANCES)
        self.assertEqual(len(DATA["decisions"]), 3)
        self.assertEqual(len(DATA["todos"]), 2)

    def test_빈_입력에서_죽지_않는다(self):
        empty = {"title": "", "summary": "", "topics": [], "decisions": [], "todos": []}
        kept, excluded = verify.verify(empty, [])
        self.assertEqual(kept, empty)
        self.assertEqual(excluded, [])

    def test_원문이_비면_모든_항목이_제외된다(self):
        kept, excluded = verify.verify(DATA, [])
        self.assertEqual(kept["decisions"], [])
        self.assertEqual(kept["todos"], [])
        self.assertEqual(len(excluded), 5)


class RenderMinutesTest(unittest.TestCase):
    def test_근거를_번호가_아니라_시각으로_적는다(self):
        kept, _ = verify.verify(DATA, UTTERANCES)
        md = verify.render_minutes(kept, UTTERANCES)
        self.assertIn("# 배포 일정 회의", md)
        self.assertIn("## 요약\n\n배포 시점을 정하고", md)
        self.assertIn("- 배포 시점", md)
        self.assertIn("1. 다음 주에 배포한다. (근거: 00:00, 00:04)", md)
        self.assertIn("1. 문서를 정리한다. (화자1) (근거: 01:10)", md)
        self.assertNotIn("[1]", md)
        self.assertNotIn("예산을 두 배로", md)

    def test_빈_결과에서_죽지_않는다(self):
        empty = {"title": "제목", "summary": "", "topics": [], "decisions": [], "todos": []}
        md = verify.render_minutes(empty, [])
        self.assertIn("## 요약\n\n(없음)", md)
        self.assertIn("## 결정사항\n\n- (없음)", md)
        self.assertIn("## 할 일\n\n- (없음)", md)


class RunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "extraction.json").write_text(json.dumps(DATA, ensure_ascii=False), encoding="utf-8")
        (self.tmp / "utterances.json").write_text(json.dumps(UTTERANCES, ensure_ascii=False), encoding="utf-8")

    def test_세_파일을_만든다(self):
        kept, excluded = verify.run(self.tmp)
        self.assertEqual(kept["decisions"], [GOOD_DECISION])
        self.assertTrue((self.tmp / "minutes.md").exists())
        self.assertEqual(json.loads((self.tmp / "verified.json").read_text(encoding="utf-8")), kept)
        saved = json.loads((self.tmp / "excluded.json").read_text(encoding="utf-8"))
        self.assertEqual(saved, excluded)
        self.assertEqual(len(saved), 3)

    def test_3단계_결과가_없으면_종료한다(self):
        with self.assertRaises(SystemExit):
            verify.run(Path(tempfile.mkdtemp()))


if __name__ == "__main__":
    unittest.main()

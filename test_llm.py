"""3단계(llm.py) 테스트. 실행: python -m unittest test_llm -v

Claude API 는 부르지 않는다. 응답을 흉내 낸 가짜 객체로 파싱·검토 파일·재실행 동작만 확인한다.
표본은 실제 회의가 아니라 지어낸 발언이다.
"""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import llm


def utt(no: int, start: float, speaker: str, text: str) -> dict:
    return {"no": no, "start": start, "speaker": speaker, "text": text}


UTTERANCES = [
    utt(1, 0.0, "화자1", "다음 주에 배포하죠"),
    utt(2, 4.5, "화자2", "네 좋습니다"),
    utt(3, 70.0, "화자1", "제가 문서를 정리할게요"),
]

DATA = {
    "title": "배포 일정 회의",
    "summary": "배포 시점을 논의해 다음 주 배포로 정했고, 화자1이 문서 정리를 맡기로 했다.",
    "topics": ["배포 시점", "문서 정리"],
    "decisions": [{"text": "다음 주에 배포한다.", "evidence": [1, 2]}],
    "todos": [{"text": "문서를 정리한다.", "owner": "화자1", "due": "", "evidence": [3, 99]}],
}


class ParseResponseTest(unittest.TestCase):
    def test_추론_블록을_건너뛰고_텍스트_블록을_JSON_으로_읽는다(self):
        content = [
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="text", text=json.dumps(DATA, ensure_ascii=False)),
        ]
        self.assertEqual(llm.parse_response(content), DATA)

    def test_텍스트_블록이_없으면_종료한다(self):
        with self.assertRaises(SystemExit):
            llm.parse_response([SimpleNamespace(type="thinking", thinking="")])


class RenderReviewTest(unittest.TestCase):
    def test_근거_번호_옆에_실제_발언이_붙는다(self):
        md = llm.render_review(DATA, UTTERANCES)
        self.assertIn("# 배포 일정 회의", md)
        self.assertIn("## 요약\n\n배포 시점을 논의해", md)
        self.assertIn("## 대화 주제\n\n- 배포 시점", md)
        self.assertIn("1. 다음 주에 배포한다.", md)
        self.assertIn("  - [1] 00:00 화자1: 다음 주에 배포하죠", md)
        self.assertIn("  - [2] 00:04 화자2: 네 좋습니다", md)
        self.assertIn("1. 문서를 정리한다. (화자1)", md)
        self.assertIn("  - [3] 01:10 화자1: 제가 문서를 정리할게요", md)

    def test_원문에_없는_번호는_표시만_하고_죽지_않는다(self):
        md = llm.render_review(DATA, UTTERANCES)
        self.assertIn("  - [99] (원문에 없는 번호)", md)

    def test_빈_결과에서_죽지_않는다(self):
        empty = {"title": "제목", "summary": "", "topics": [], "decisions": [], "todos": []}
        md = llm.render_review(empty, [])
        self.assertIn("## 요약\n\n(없음)", md)
        self.assertIn("## 대화 주제\n\n- (없음)", md)
        self.assertIn("## 결정사항\n\n- (없음)", md)
        self.assertIn("## 할 일\n\n- (없음)", md)


class CostTest(unittest.TestCase):
    def test_토큰_수를_달러로_바꾼다(self):
        usage = SimpleNamespace(input_tokens=1_000_000, output_tokens=100_000)
        self.assertAlmostEqual(llm.cost_usd(usage), 5.0 + 2.5)


class RunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "transcript.md").write_text("| 번호 | 시각 | 화자 | 내용 |\n", encoding="utf-8")
        (self.tmp / "utterances.json").write_text(json.dumps(UTTERANCES, ensure_ascii=False), encoding="utf-8")

    def _fake_response(self):
        usage = SimpleNamespace(input_tokens=10, output_tokens=5, to_dict=lambda: {"input_tokens": 10, "output_tokens": 5})
        block = SimpleNamespace(type="text", text="{}", to_dict=lambda: {"type": "text", "text": "{}"})
        return SimpleNamespace(model=llm.MODEL, stop_reason="end_turn", usage=usage, content=[block])

    def test_세_파일을_만든다(self):
        with mock.patch.object(llm, "extract", return_value=(DATA, self._fake_response())):
            result = llm.run(self.tmp)
        self.assertEqual(result, DATA)
        self.assertEqual(json.loads((self.tmp / "extraction.json").read_text(encoding="utf-8")), DATA)
        self.assertTrue((self.tmp / "extraction_review.md").exists())
        self.assertTrue((self.tmp / "llm_response.json").exists())

    def test_결과가_있으면_다시_호출하지_않는다(self):
        (self.tmp / "extraction.json").write_text(json.dumps(DATA, ensure_ascii=False), encoding="utf-8")
        with mock.patch.object(llm, "extract") as fake:
            result = llm.run(self.tmp)
        fake.assert_not_called()
        self.assertEqual(result, DATA)

    def test_force_면_결과가_있어도_다시_호출한다(self):
        (self.tmp / "extraction.json").write_text("{}", encoding="utf-8")
        with mock.patch.object(llm, "extract", return_value=(DATA, self._fake_response())) as fake:
            llm.run(self.tmp, force=True)
        fake.assert_called_once()

    def test_2단계_결과가_없으면_종료한다(self):
        with self.assertRaises(SystemExit):
            llm.run(Path(tempfile.mkdtemp()))


if __name__ == "__main__":
    unittest.main()

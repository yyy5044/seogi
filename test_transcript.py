"""2단계(transcript.py) 고정 표본 테스트. 실행: python -m unittest test_transcript -v

표본은 실제 회의가 아니라 지어낸 단어 목록이다 (원문은 저장소에 올리지 않는다).
"""

import json
import tempfile
import unittest
from pathlib import Path

from transcript import build, format_time, group_utterances


def word(speaker: str, text: str, sec: int, nanos: int = 0) -> dict:
    """다글로 응답의 단어 하나를 흉내 낸다. seconds 는 실제 응답처럼 문자열이다."""
    return {
        "speaker": speaker,
        "word": text,
        "startTime": {"seconds": str(sec), "nanos": nanos},
        "endTime": {"seconds": str(sec + 1), "nanos": 0},
        "segmentId": "9",  # 쓰지 않는 필드. 있어도 영향이 없어야 한다.
    }


class GroupUtterancesTest(unittest.TestCase):
    def test_화자가_바뀌면_발언이_끊긴다(self):
        words = [word("1", "안녕", 0), word("1", " 하세요", 1), word("2", " 네", 2)]
        utts = group_utterances(words)
        self.assertEqual(len(utts), 2)
        self.assertEqual(utts[0]["speaker"], "화자1")
        self.assertEqual(utts[0]["text"], "안녕 하세요")
        self.assertEqual(utts[1]["speaker"], "화자2")
        self.assertEqual(utts[1]["text"], "네")

    def test_같은_화자가_돌아와도_별개_발언이다(self):
        words = [word("1", "먼저", 0), word("2", " 네", 1), word("1", " 그래서", 2)]
        utts = group_utterances(words)
        self.assertEqual([u["speaker"] for u in utts], ["화자1", "화자2", "화자1"])
        self.assertEqual([u["no"] for u in utts], [1, 2, 3])

    def test_마지막_발언이_사라지지_않는다(self):
        utts = group_utterances([word("1", "하나", 0), word("2", " 둘", 5)])
        self.assertEqual(utts[-1]["text"], "둘")
        self.assertEqual(utts[-1]["start"], 5.0)

    def test_시각은_첫_단어_기준이다(self):
        words = [word("1", "가", 3, 500_000_000), word("1", " 나", 7)]
        utts = group_utterances(words)
        self.assertEqual(len(utts), 1)
        self.assertAlmostEqual(utts[0]["start"], 3.5)

    def test_빈_입력에서_죽지_않는다(self):
        self.assertEqual(group_utterances([]), [])


class FormatTimeTest(unittest.TestCase):
    def test_분초(self):
        self.assertEqual(format_time(0), "00:00")
        self.assertEqual(format_time(65.9), "01:05")

    def test_한_시간_이상(self):
        self.assertEqual(format_time(3661), "1:01:01")


class BuildTest(unittest.TestCase):
    def _run(self, body: dict) -> tuple[list[dict], Path]:
        tmp = Path(tempfile.mkdtemp())
        (tmp / "stt_response.json").write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
        return build(tmp), tmp

    def test_빈_sttResults_에서_죽지_않고_빈_파일을_만든다(self):
        utts, tmp = self._run({"status": "transcribed", "sttResults": []})
        self.assertEqual(utts, [])
        self.assertTrue((tmp / "transcript.md").exists())
        self.assertEqual(json.loads((tmp / "utterances.json").read_text(encoding="utf-8")), [])

    def test_표가_만들어진다(self):
        body = {"sttResults": [{"transcript": "안녕 하세요 네", "words": [
            word("1", "안녕", 0), word("1", " 하세요", 1), word("2", " 네", 2)]}]}
        utts, tmp = self._run(body)
        md = (tmp / "transcript.md").read_text(encoding="utf-8").splitlines()
        self.assertEqual(md[0], "| 번호 | 시각 | 화자 | 내용 |")
        self.assertEqual(md[2], "| 1 | 00:00 | 화자1 | 안녕 하세요 |")
        self.assertEqual(md[3], "| 2 | 00:02 | 화자2 | 네 |")
        self.assertEqual(len(utts), 2)


if __name__ == "__main__":
    unittest.main()

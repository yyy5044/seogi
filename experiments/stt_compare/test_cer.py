"""cer.py 테스트. 실행: (저장소 루트에서) python -m unittest experiments.stt_compare.test_cer -v"""

import unittest

from experiments.stt_compare.cer import cer, extract_text, normalize


class NormalizeTest(unittest.TestCase):
    def test_공백과_문장부호를_지운다(self):
        self.assertEqual(normalize("안녕, 하세요. 네!"), "안녕하세요네")

    def test_영문은_소문자로(self):
        self.assertEqual(normalize("Persona Ace"), "personaace")


class ExtractTextTest(unittest.TestCase):
    def test_표면_내용_열만_뽑는다(self):
        md = "| 번호 | 시각 | 화자 | 내용 |\n|---|---|---|---|\n| 1 | 00:00 | 화자1 | 안녕 |\n| 2 | 00:05 | 화자2 | 네 |\n"
        self.assertEqual(extract_text(md), "안녕\n네")

    def test_표가_아니면_그대로(self):
        self.assertEqual(extract_text("안녕 하세요"), "안녕 하세요")


class CerTest(unittest.TestCase):
    def test_같으면_0(self):
        self.assertEqual(cer("안녕하세요", "안녕하세요")["cer"], 0.0)

    def test_띄어쓰기_구두점_차이는_오류가_아니다(self):
        self.assertEqual(cer("안녕하세요. 네", "안녕 하세요 네.")["cer"], 0.0)

    def test_치환_하나(self):
        r = cer("안녕하세요", "안녕하새요")
        self.assertEqual((r["substitutions"], r["deletions"], r["insertions"]), (1, 0, 0))
        self.assertAlmostEqual(r["cer"], 0.2)

    def test_삭제와_삽입(self):
        r = cer("안녕하세요", "안녕세요")        # 1글자 빠짐
        self.assertEqual(r["deletions"], 1)
        r = cer("안녕하세요", "안녕하세요요")    # 1글자 늘어남
        self.assertEqual(r["insertions"], 1)

    def test_인식결과가_비면_전부_삭제(self):
        self.assertEqual(cer("안녕", "")["cer"], 1.0)

    def test_정답이_비면_오류(self):
        with self.assertRaises(ValueError):
            cer("", "안녕")


if __name__ == "__main__":
    unittest.main()

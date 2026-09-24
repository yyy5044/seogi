"""CER(문자 오류율) 계산. 정답 원고와 인식 결과를 비교한다.

사용법: (저장소 루트에서) python stt_eval/scripts/cer.py <정답.txt> <인식결과.txt> [<인식결과2.txt> ...]

CER = (치환 + 삭제 + 삽입) / 정답 글자 수
비교 전에 공백과 문장 부호를 모두 지우고 소문자로 맞춘다.
띄어쓰기·구두점 차이는 회의록 품질과 무관하므로 오류로 세지 않기 위해서다.
입력이 transcript.md 같은 표(| 번호 | 시각 | 화자 | 내용 |)면 내용 열만 뽑아 비교한다.
"""

import sys
import unicodedata
from pathlib import Path


def normalize(text: str) -> str:
    """유니코드 정규화(NFC) 뒤 공백·문장 부호를 지우고 소문자로 만든다."""
    text = unicodedata.normalize("NFC", text).lower()
    return "".join(
        ch for ch in text
        if not ch.isspace() and not unicodedata.category(ch).startswith("P")
    )


def extract_text(raw: str) -> str:
    """표 형식이면 마지막 열(내용)만 이어 붙이고, 아니면 그대로 돌려준다."""
    rows = [line for line in raw.splitlines() if line.lstrip().startswith("|")]
    if not rows:
        return raw
    texts = []
    for row in rows:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if not cells or cells[0] in ("번호", "") or set(cells[0]) <= set("-:"):
            continue  # 헤더, 구분선
        texts.append(cells[-1])
    return "\n".join(texts)


def edit_distance(ref: str, hyp: str) -> tuple[int, int, int]:
    """레벤슈타인 거리를 (치환, 삭제, 삽입) 으로 나눠 돌려준다."""
    n, m = len(ref), len(hyp)
    # dp[i][j] = ref[:i] 를 hyp[:j] 로 바꾸는 최소 편집 수
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = i
    for j in range(1, m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j - 1] + cost, dp[i - 1][j] + 1, dp[i][j - 1] + 1)

    # 역추적해서 종류별로 센다
    sub = dele = ins = 0
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + (0 if ref[i - 1] == hyp[j - 1] else 1):
            if ref[i - 1] != hyp[j - 1]:
                sub += 1
            i, j = i - 1, j - 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            dele += 1
            i -= 1
        else:
            ins += 1
            j -= 1
    return sub, dele, ins


def cer(reference: str, hypothesis: str) -> dict:
    """정규화한 두 문자열의 CER 과 세부 수치를 돌려준다."""
    ref, hyp = normalize(reference), normalize(hypothesis)
    if not ref:
        raise ValueError("정답 원고가 비어 있습니다.")
    sub, dele, ins = edit_distance(ref, hyp)
    return {
        "ref_chars": len(ref),
        "hyp_chars": len(hyp),
        "substitutions": sub,
        "deletions": dele,
        "insertions": ins,
        "cer": (sub + dele + ins) / len(ref),
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("사용법: (저장소 루트에서) python stt_eval/scripts/cer.py <정답.txt> <인식결과.txt> [<인식결과2.txt> ...]")
    reference = extract_text(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(f"정답: {sys.argv[1]}")
    for path in sys.argv[2:]:
        r = cer(reference, extract_text(Path(path).read_text(encoding="utf-8")))
        print(
            f"  {path}: CER {r['cer']:.1%}  "
            f"(정답 {r['ref_chars']}자, 치환 {r['substitutions']} / 삭제 {r['deletions']} / 삽입 {r['insertions']})"
        )

"""전체 실행: 녹음 파일 하나 → 노션 회의록 페이지.

사용법: python run.py <녹음 파일>
1단계 다글로 음성 인식 → 2단계 원문 만들기 → 3단계 Claude 추출 → 4단계 근거 검증 → 5단계 노션 기록.
각 단계는 runs/<회의ID>/ 의 파일로 이어지고, 결과가 이미 있는 단계(1·3단계)는 다시 부르지 않는다.
어느 단계든 실패하면 거기서 멈추고 노션 페이지는 만들지 않는다. 단계별 소요 시간을 마지막에 출력한다.
"""

import sys
import time
from pathlib import Path

import daglo
import transcript
import llm
import verify
import notion


def main(audio_path: Path) -> str:
    timings = []

    def step(name: str, fn):
        print(f"\n[{name}]")
        started = time.monotonic()
        result = fn()
        timings.append((name, time.monotonic() - started))
        return result

    run_dir = step("1단계 음성 인식", lambda: daglo.transcribe(audio_path))
    step("2단계 원문 만들기", lambda: transcript.build(run_dir))
    step("3단계 추출", lambda: llm.run(run_dir))
    step("4단계 근거 검증", lambda: verify.run(run_dir))
    url = step("5단계 노션 기록", lambda: notion.run(run_dir))

    print("\n단계별 소요 시간")
    for name, sec in timings:
        print(f"  {name}: {sec:.1f}초")
    print(f"합계: {sum(s for _, s in timings):.1f}초")
    return url


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("사용법: python run.py <녹음 파일>")
    path = Path(sys.argv[1])
    if not path.is_file():
        sys.exit(f"파일이 없습니다: {path}")
    main(path)

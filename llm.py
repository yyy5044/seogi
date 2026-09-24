"""Claude API 호출 (3단계: 추출).

사용법: python llm.py runs/<회의ID>   (또는 회의ID 만)
        python llm.py runs/<회의ID> --force   (이미 결과가 있어도 다시 호출. 프롬프트를 다듬을 때 쓴다)
입력:   runs/<회의ID>/transcript.md         (2단계 결과. LLM 에 그대로 보낸다)
        runs/<회의ID>/utterances.json       (검토용 파일에 근거 발언 내용을 붙일 때 쓴다)
        prompts/extract.md                  (시스템 프롬프트. 결과를 다듬을 때 이 파일을 고친다)
출력:   runs/<회의ID>/extraction.json       (제목·안건·결정사항·할 일. 결정사항과 할 일에는 근거 발언 번호)
        runs/<회의ID>/extraction_review.md  (사람이 눈으로 검토하기 위한 파일. 근거 번호 옆에 실제 발언을 붙인다)
        runs/<회의ID>/llm_response.json     (응답 원본과 토큰 사용량)

API 키는 환경 변수 ANTHROPIC_API_KEY 에서만 읽는다. LLM 호출은 1회다.
응답은 JSON 스키마(SCHEMA)에 맞는 형식이 API 수준에서 보장되지만, 근거 번호가 진짜인지는 4단계가 확인한다.
"""

import json
import os
import sys
import time
from pathlib import Path

import anthropic

from transcript import format_time

MODEL = "claude-opus-5"
MAX_TOKENS = 16000
PRICE_PER_MTOK = {"input": 5.0, "output": 25.0}  # 미국 달러, 100만 토큰당
RUNS_DIR = Path("runs")
PROMPT_FILE = Path(__file__).parent / "prompts" / "extract.md"

# 근거 번호를 붙이는 항목(결정사항, 할 일)의 공통 구조
_ITEM_WITH_EVIDENCE = {
    "text": {"type": "string", "description": "정리된 한 문장"},
    "evidence": {
        "type": "array",
        "items": {"type": "integer"},
        "description": "근거가 된 발언 번호. 원문 표에 실제로 있는 번호만",
    },
}

# LLM 응답이 반드시 따라야 하는 형식. API 가 이 스키마에 맞는 JSON 만 돌려준다.
SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "회의 내용을 한 줄로 요약한 제목"},
        "agenda": {"type": "array", "items": {"type": "string"}, "description": "다룬 주제 목록"},
        "decisions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": _ITEM_WITH_EVIDENCE,
                "required": ["text", "evidence"],
                "additionalProperties": False,
            },
        },
        "todos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    **_ITEM_WITH_EVIDENCE,
                    "owner": {"type": "string", "description": "담당자. 화자 번호 그대로(화자1). 없으면 빈 문자열"},
                    "due": {"type": "string", "description": "기한. 원문에 말한 그대로. 없으면 빈 문자열"},
                },
                "required": ["text", "owner", "due", "evidence"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "agenda", "decisions", "todos"],
    "additionalProperties": False,
}


def _client() -> anthropic.Anthropic:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("환경 변수 ANTHROPIC_API_KEY 가 없습니다.")
    return anthropic.Anthropic()


def load_prompt() -> str:
    """prompts/extract.md 를 읽어 시스템 프롬프트로 쓴다."""
    if not PROMPT_FILE.exists():
        sys.exit(f"프롬프트 파일이 없습니다: {PROMPT_FILE}")
    return PROMPT_FILE.read_text(encoding="utf-8")


def extract(transcript_md: str, prompt: str) -> tuple[dict, anthropic.types.Message]:
    """원문 표를 Claude 에 보내 추출 결과(dict)와 응답 객체를 돌려준다. 호출은 1회."""
    response = _client().messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=prompt,
        messages=[{"role": "user", "content": transcript_md}],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    )
    if response.stop_reason == "refusal":
        sys.exit(f"모델이 응답을 거부했습니다: {response.stop_details}")
    if response.stop_reason == "max_tokens":
        sys.exit(f"응답이 {MAX_TOKENS} 토큰에서 잘렸습니다. MAX_TOKENS 를 올리세요.")
    return parse_response(response.content), response


def parse_response(content: list) -> dict:
    """응답 블록 목록에서 텍스트 블록을 찾아 JSON 으로 읽는다 (추론 블록 등은 건너뛴다)."""
    text = next((b.text for b in content if b.type == "text"), None)
    if text is None:
        sys.exit("응답에 텍스트 블록이 없습니다.")
    return json.loads(text)


def cost_usd(usage) -> float:
    """토큰 사용량 → 달러. 캐시는 쓰지 않으므로 입력·출력만 센다."""
    return (
        usage.input_tokens * PRICE_PER_MTOK["input"] + usage.output_tokens * PRICE_PER_MTOK["output"]
    ) / 1_000_000


def render_review(data: dict, utterances: list[dict]) -> str:
    """추출 결과와 발언 목록 → 검토용 마크다운.

    결정사항과 할 일의 근거 번호마다 실제 발언(시각, 화자, 내용)을 붙여서
    원문을 오가지 않고 "이 근거가 맞나" 를 한 화면에서 판단할 수 있게 한다.
    원문에 없는 번호는 그대로 표시만 한다. 빼는 것은 4단계 일이다.
    """
    by_no = {u["no"]: u for u in utterances}

    def evidence_lines(nos: list[int]) -> list[str]:
        lines = []
        for no in nos:
            u = by_no.get(no)
            if u is None:
                lines.append(f"  - [{no}] (원문에 없는 번호)")
            else:
                lines.append(f"  - [{no}] {format_time(u['start'])} {u['speaker']}: {u['text']}")
        return lines or ["  - (근거 없음)"]

    out = [f"# {data['title']}", "", "## 안건", ""]
    out += [f"- {a}" for a in data["agenda"]] or ["- (없음)"]

    out += ["", "## 결정사항", ""]
    if not data["decisions"]:
        out.append("- (없음)")
    for i, d in enumerate(data["decisions"], start=1):
        out.append(f"{i}. {d['text']}")
        out += evidence_lines(d["evidence"])

    out += ["", "## 할 일", ""]
    if not data["todos"]:
        out.append("- (없음)")
    for i, t in enumerate(data["todos"], start=1):
        meta = " / ".join(x for x in (t.get("owner", ""), t.get("due", "")) if x)
        out.append(f"{i}. {t['text']}" + (f" ({meta})" if meta else ""))
        out += evidence_lines(t["evidence"])

    return "\n".join(out) + "\n"


def run(run_dir: Path, force: bool = False) -> dict:
    """runs/<회의ID>/transcript.md → extraction.json, extraction_review.md. 추출 결과를 돌려준다."""
    transcript_file = run_dir / "transcript.md"
    utterances_file = run_dir / "utterances.json"
    if not transcript_file.exists() or not utterances_file.exists():
        sys.exit(f"2단계 결과가 없습니다: {run_dir} (transcript.py 를 먼저 실행하세요)")

    extraction_file = run_dir / "extraction.json"
    if extraction_file.exists() and not force:
        print(f"이미 결과가 있습니다: {extraction_file} (다시 호출하려면 --force)")
        return json.loads(extraction_file.read_text(encoding="utf-8"))

    prompt = load_prompt()
    transcript_md = transcript_file.read_text(encoding="utf-8")
    utterances = json.loads(utterances_file.read_text(encoding="utf-8"))

    print(f"Claude 호출 중: {MODEL}, 발언 {len(utterances)}개")
    started = time.monotonic()
    data, response = extract(transcript_md, prompt)
    elapsed = time.monotonic() - started

    extraction_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "extraction_review.md").write_text(render_review(data, utterances), encoding="utf-8")
    (run_dir / "llm_response.json").write_text(
        json.dumps(
            {"model": response.model, "stop_reason": response.stop_reason,
             "usage": response.usage.to_dict(), "content": [b.to_dict() for b in response.content]},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )

    u = response.usage
    print(
        f"완료 ({elapsed:.0f}초): 안건 {len(data['agenda'])}개, 결정사항 {len(data['decisions'])}개, "
        f"할 일 {len(data['todos'])}개 / 토큰 입력 {u.input_tokens} 출력 {u.output_tokens} "
        f"약 ${cost_usd(u):.3f}"
    )
    print(f"저장: {extraction_file}, 검토용: {run_dir / 'extraction_review.md'}")
    return data


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--force"]
    if len(args) != 1:
        sys.exit("사용법: python llm.py runs/<회의ID> [--force]")
    arg = Path(args[0])
    run_dir = arg if arg.is_dir() else RUNS_DIR / args[0]
    if not run_dir.is_dir():
        sys.exit(f"폴더가 없습니다: {run_dir}")
    run(run_dir, force="--force" in sys.argv)

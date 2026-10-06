"""LLM 교정 단계 실험 (2026-10-06 당시 스크립트 보존).

사용법: (저장소 루트에서) python experiments/correction/correct.py <회의ID> <방식> [--context "회의 한 줄 설명"]
        [--glossary 단어 사전 파일] [--out 출력 폴더 이름 (기본: 방식 이름)] [--model 모델 ID (기본: claude-opus-5-5)]
  방식 none  : 교정 없이 원문 그대로 추출 (대조군. 추출도 LLM 이라 실행마다 달라서 같은 조건으로 다시 돌린다)
       plain : docs/spec.md "계획: 교정 단계 추가" 규칙대로 교정한 뒤 추출
       mark  : plain 규칙 + 고칠 확신이 없는데 뜻이 안 통하는 말은 [불명확: 원래 표기] 로 표시.
               추출 프롬프트에 "표시된 말로 주제·결정·할 일을 만들지 않는다" 를 덧붙인다
예:   python experiments/correction/correct.py 2bfc0703de20ad5a mark

입력: runs/<회의ID>/utterances.json (2단계 결과. 고치지 않는다), prompts/extract.md (추출 프롬프트, 그대로 읽기만)
출력: runs/_experiments/correction/<회의ID>/<방식>/
      utterances.json, transcript.md (교정본. none 은 원문 그대로), corrections.md (고친 발언 전후),
      correction_response.json, extraction.json, extraction_review.md, extract_prompt.md (실제로 쓴 추출 프롬프트)

교정 호출에는 발언 번호와 내용만 보내고 화자·시각은 코드가 그대로 붙인다.
응답의 번호 집합·개수가 원본과 다르면 종료한다. 발언 80개씩 나눠 호출한다.
API 키는 환경 변수 ANTHROPIC_API_KEY. 다른 폴더에 기대지 않도록 추출 호출 코드도 이 파일에 둔다.
"""

import json
import os
import sys
import time
from pathlib import Path

import anthropic

MODEL = "claude-opus-5-5"
MAX_TOKENS = 16000
PRICE_PER_MTOK = {  # 미국 달러, 100만 토큰당 (2026-09-25 기준)
    "claude-opus-5-5": {"input": 4.0, "output": 20.0},
    "claude-sonnet-5-5": {"input": 2.0, "output": 10.0},
}
CHUNK = 80
RUNS_DIR = Path("runs")
OUT_DIR = RUNS_DIR / "_experiments" / "correction"
EXTRACT_PROMPT_FILE = Path("prompts") / "extract.md"
MODES = ("none", "plain", "mark")

CORRECT_PROMPT = """너는 한국어 회의 음성 인식(STT) 결과를 교정한다.

입력은 발언 목록 JSON 이다: [{"no": 발언 번호, "text": 내용}, ...]. 같은 번호, 같은 개수로 교정본을 돌려준다.

규칙:
- 발음이 비슷해서 잘못 적힌 단어만, 앞뒤 맥락으로 뜻이 통하게 고친다. 예: "기업 발표" 가 맥락상 "기획 발표" 라면 고친다.
- 말을 더하거나 빼지 않는다. 말투, 군말("그", "이제", "뭔가"), 반복, 문법, 띄어쓰기, 문장 부호는 손대지 않는다.
- 확신이 없으면 그대로 둔다. 그럴듯한 다른 말로 바꾸는 것보다 틀린 그대로 두는 것이 낫다.
- 고칠 것이 없는 발언은 text 를 입력과 글자 하나 다르지 않게 그대로 돌려준다.
"""

MARK_RULE = """- 존재하지 않는 말이거나 맥락에 어울리지 않는 말인데 고칠 확신이 없으면, 지우지 말고 [불명확: 원래 표기] 로 감싼다. 예: "짜갱이라는 거기에" → "[불명확: 짜갱이]라는 거기에". 단어 하나 또는 몇 글자만 감싸고 문장 전체를 감싸지 않는다.
"""

EXTRACT_MARK_RULE = """

## 음성 인식 불명확 표시

원문에 [불명확: ...] 로 감싼 말은 음성 인식이 틀렸을 가능성이 큰 말이다. 이 말의 뜻을 추정하지 말고, 이 말을 대화 주제·결정사항·할 일의 핵심어로 쓰지 않는다. 요약에서 언급해야 하면 "알아듣기 어려운 표현" 으로 적는다.
"""

CORRECT_SCHEMA = {
    "type": "object",
    "properties": {
        "utterances": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"no": {"type": "integer"}, "text": {"type": "string"}},
                "required": ["no", "text"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["utterances"],
    "additionalProperties": False,
}

# 루트 llm.py 의 SCHEMA 와 같은 형식 (실험 당시 복사본)
_ITEM_WITH_EVIDENCE = {
    "text": {"type": "string", "description": "정리된 한 문장"},
    "evidence": {"type": "array", "items": {"type": "integer"}, "description": "근거가 된 발언 번호. 원문 표에 실제로 있는 번호만"},
}
EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "회의 내용을 한 줄로 요약한 제목"},
        "summary": {"type": "string", "description": "원문을 대신할 수 있는 회의 서술. 주제별로 문단을 나누고 문단 사이는 빈 줄. 길이 제한 없음"},
        "topics": {"type": "array", "items": {"type": "string"}, "description": "회의에서 오간 대화 주제 목록"},
        "decisions": {
            "type": "array",
            "items": {"type": "object", "properties": _ITEM_WITH_EVIDENCE, "required": ["text", "evidence"], "additionalProperties": False},
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
    "required": ["title", "summary", "topics", "decisions", "todos"],
    "additionalProperties": False,
}


# ---------- 공통 ----------

def _client() -> anthropic.Anthropic:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("환경 변수 ANTHROPIC_API_KEY 가 없습니다.")
    return anthropic.Anthropic()


def call(system: str, user: str, schema: dict) -> tuple[dict, anthropic.types.Message]:
    response = _client().messages.create(
        model=MODEL,  # --model 로 바꿀 수 있다 (모듈 변수를 덮어씀)
        max_tokens=MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": schema}},
    )
    if response.stop_reason == "refusal":
        sys.exit(f"모델이 응답을 거부했습니다: {response.stop_details}")
    if response.stop_reason == "max_tokens":
        sys.exit(f"응답이 {MAX_TOKENS} 토큰에서 잘렸습니다.")
    text = next((b.text for b in response.content if b.type == "text"), None)
    if text is None:
        sys.exit("응답에 텍스트 블록이 없습니다.")
    return json.loads(text), response


def cost_usd(usage) -> float:
    price = PRICE_PER_MTOK[MODEL]
    return (usage.input_tokens * price["input"] + usage.output_tokens * price["output"]) / 1_000_000


def format_time(seconds: float) -> str:
    s = int(seconds)
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"


def transcript_md(utterances: list[dict]) -> str:
    lines = ["| 번호 | 시각 | 화자 | 내용 |", "|---|---|---|---|"]
    for u in utterances:
        text = u["text"].replace("|", "\\|")
        lines.append(f"| {u['no']} | {format_time(u['start'])} | {u['speaker']} | {text} |")
    return "\n".join(lines) + "\n"


# ---------- 교정 ----------

def correct(utterances: list[dict], mode: str, context: str, glossary: str) -> tuple[list[dict], list[dict]]:
    """발언 목록 → (교정된 발언 목록, 호출별 응답 기록). 화자·시각은 원본에서 그대로 가져온다."""
    system = CORRECT_PROMPT + (MARK_RULE if mode == "mark" else "")
    if context:
        system += f"\n회의 맥락: {context}\n"
    if glossary:
        system += (
            "\n단어 사전 (이 회의·팀에서 쓰는 말. 발음이 비슷한데 뜻이 안 통하는 말이 있으면 이 단어일 가능성을 먼저 본다."
            " 사전에 있다고 해서 발음이 다른 말을 이 단어로 바꾸지는 않는다):\n" + glossary + "\n"
        )

    fixed: dict[int, str] = {}
    log = []
    for i in range(0, len(utterances), CHUNK):
        chunk = utterances[i : i + CHUNK]
        payload = json.dumps([{"no": u["no"], "text": u["text"]} for u in chunk], ensure_ascii=False)
        data, response = call(system, payload, CORRECT_SCHEMA)
        got = data["utterances"]
        want_nos = [u["no"] for u in chunk]
        if sorted(x["no"] for x in got) != sorted(want_nos):
            sys.exit(f"교정 응답의 발언 번호가 원본과 다릅니다 (발언 {want_nos[0]}~{want_nos[-1]}). 응답 개수 {len(got)}, 원본 {len(chunk)}")
        fixed.update({x["no"]: x["text"] for x in got})
        log.append({"system": system, "usage": response.usage.to_dict(), "cost_usd": cost_usd(response.usage), "utterances": got})
        print(f"  교정 {want_nos[0]}~{want_nos[-1]}: 입력 {response.usage.input_tokens} 출력 {response.usage.output_tokens} 약 ${cost_usd(response.usage):.3f}")

    return [{**u, "text": fixed[u["no"]]} for u in utterances], log


def corrections_md(before: list[dict], after: list[dict]) -> tuple[str, int]:
    """원본과 교정본을 비교해 바뀐 발언만 전후로 적는다. (마크다운, 바뀐 발언 수)"""
    out = ["# 교정 목록", ""]
    n = 0
    for b, a in zip(before, after):
        if b["text"] == a["text"]:
            continue
        n += 1
        out += [f"## [{b['no']}] {format_time(b['start'])} {b['speaker']}", "", f"- 전: {b['text']}", f"- 후: {a['text']}", ""]
    if n == 0:
        out.append("(바뀐 발언 없음)")
    return "\n".join(out) + "\n", n


# ---------- 추출 (루트 llm.py 와 같은 호출) ----------

def render_review(data: dict, utterances: list[dict]) -> str:
    by_no = {u["no"]: u for u in utterances}

    def evidence_lines(nos: list[int]) -> list[str]:
        lines = []
        for no in nos:
            u = by_no.get(no)
            lines.append(f"  - [{no}] (원문에 없는 번호)" if u is None else f"  - [{no}] {format_time(u['start'])} {u['speaker']}: {u['text']}")
        return lines or ["  - (근거 없음)"]

    out = [f"# {data['title']}", "", "## 요약", "", data["summary"] or "(없음)", "", "## 대화 주제", ""]
    out += [f"- {t}" for t in data["topics"]] or ["- (없음)"]
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


# ---------- 조립 ----------

def run(meeting_id: str, mode: str, context: str, glossary_file: str, out_name: str) -> None:
    src = RUNS_DIR / meeting_id / "utterances.json"
    if not src.exists():
        sys.exit(f"2단계 결과가 없습니다: {src}")
    if not EXTRACT_PROMPT_FILE.exists():
        sys.exit(f"추출 프롬프트가 없습니다: {EXTRACT_PROMPT_FILE}")
    glossary = ""
    if glossary_file:
        if not Path(glossary_file).exists():
            sys.exit(f"단어 사전 파일이 없습니다: {glossary_file}")
        glossary = Path(glossary_file).read_text(encoding="utf-8").strip()
    out = OUT_DIR / meeting_id / (out_name or mode)
    out.mkdir(parents=True, exist_ok=True)
    write = lambda name, text: (out / name).write_text(text, encoding="utf-8")

    original = json.loads(src.read_text(encoding="utf-8"))
    total = 0.0
    started = time.monotonic()

    if mode == "none":
        utterances = original
    else:
        print(
            f"[교정] {MODEL}, 발언 {len(original)}개, 방식 {mode}"
            + (f", 맥락 있음" if context else "") + (f", 단어 사전 {glossary_file}" if glossary else "")
        )
        utterances, log = correct(original, mode, context, glossary)
        total += sum(x["cost_usd"] for x in log)
        md, changed = corrections_md(original, utterances)
        write("corrections.md", md)
        write(
            "correction_response.json",
            json.dumps({"context": context, "glossary": glossary, "calls": log}, ensure_ascii=False, indent=2),
        )
        marked = sum(u["text"].count("[불명확:") for u in utterances)
        print(f"  바뀐 발언 {changed}개" + (f", 불명확 표시 {marked}개" if mode == "mark" else ""))

    write("utterances.json", json.dumps(utterances, ensure_ascii=False, indent=2))
    transcript = transcript_md(utterances)
    write("transcript.md", transcript)

    prompt = EXTRACT_PROMPT_FILE.read_text(encoding="utf-8") + (EXTRACT_MARK_RULE if mode == "mark" else "")
    write("extract_prompt.md", prompt)
    print(f"[추출] {MODEL}")
    data, response = call(prompt, transcript, EXTRACT_SCHEMA)
    total += cost_usd(response.usage)
    write("extraction.json", json.dumps(data, ensure_ascii=False, indent=2))
    write("extraction_review.md", render_review(data, utterances))
    print(f"  대화 주제 {len(data['topics'])}개, 결정사항 {len(data['decisions'])}개, 할 일 {len(data['todos'])}개")
    for t in data["topics"]:
        print(f"  - {t}")

    print(f"완료 ({time.monotonic() - started:.0f}초, 약 ${total:.3f}): {out}")


if __name__ == "__main__":
    args = sys.argv[1:]
    opts = {"--context": "", "--glossary": "", "--out": "", "--model": MODEL}
    for name in opts:
        if name in args:
            i = args.index(name)
            if i + 1 >= len(args):
                sys.exit(f"{name} 뒤에 값을 적으세요.")
            opts[name] = args[i + 1]
            del args[i : i + 2]
    if len(args) != 2 or args[1] not in MODES:
        sys.exit(
            f"사용법: python experiments/correction/correct.py <회의ID> <{'|'.join(MODES)}>"
            " [--context \"...\"] [--glossary 파일] [--out 출력 폴더 이름] [--model 모델 ID]"
        )
    if opts["--model"] not in PRICE_PER_MTOK:
        sys.exit(f"모르는 모델입니다: {opts['--model']} (가능: {', '.join(PRICE_PER_MTOK)})")
    MODEL = opts["--model"]
    run(args[0], args[1], opts["--context"], opts["--glossary"], opts["--out"])

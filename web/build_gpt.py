"""ChatGPT 맞춤 GPT / Gemini Gem용 설정 파일을 만든다.

python web/build_gpt.py OUT_DIR
- instructions.txt: '지침(Instructions)' 칸에 붙여 넣을 내용 (8000자 이하)
- examples.md: '지식(Knowledge)' 파일로 올릴 실제 대화 예시
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MOOD_NAME = {"ff": "기분좋음", "nn": "평범", "ss": "기분안좋음"}
ROOM_NAME = {"dm": "개인톡", "group": "전체톡"}


def bullets(items):
    return "\n".join(f"- {t}" for t in items)


def build(style):
    instructions = f"""너는 AISL 연구실 지도교수님이 카카오톡으로 학생에게 보낼 답장을 예측하는 도우미다.
학생이 교수님께 보낼 메시지를 주면, 교수님이 지정된 기분일 때 보낼 법한 답장을 쓴다.
이것은 재미와 연습용 예측이며 교수님이 실제로 한 말이 아니다.

## 입력 읽는 법
사용자는 보통 이렇게 보낸다: "ss 전체톡 박사3 교수님 다음주 세미나 줌으로 참석해도 될까요?"
- 기분: ff(기분좋음), nn(평범), ss(기분안좋음). 없으면 nn.
- 대화방: 개인톡 또는 전체톡. 없으면 개인톡.
- 보내는 사람: 석사/박사/석박통합 + 연차(예: 박사3, 석사2). 없으면 박사 3년차. 석박통합은 1~2년차는 석사, 3년차부터 박사로 본다.
- 나머지가 학생 메시지다.
정보가 빠져도 되묻지 말고 기본값으로 바로 답한다.

## 기분
{bullets(f"{k} {MOOD_NAME[k]}: {v.split(': ', 1)[-1]}" for k, v in style["moods"].items())}

## 대화방
{bullets(style["rooms"].values())}

## 연구실
{bullets(style["lab"])}

## 교수님의 기준 (가장 중요, 기분보다 우선)
{bullets(style["priorities"])}

## 교수님의 습관
{bullets(style["habits"])}

## 말투
{bullets(style["traits"])}

## 실제 예시
지식 파일 examples.md에 실제 대화 예시가 기분·대화방별로 있다. 답하기 전에 같은 기분, 같은 대화방 예시를 먼저 참고하고 말투와 길이를 맞춘다. 예시 문장을 그대로 베끼지 말고 이 메시지에 맞게 쓴다.

## 출력 형식
- 첫 줄에 [기분 · 대화방 · 보내는 사람]을 짧게 쓴다. 예: [ss 기분안좋음 · 전체톡 · 박사 3년차]
- 그다음 교수님이 보낼 카톡 메시지만 한 줄에 하나씩 1~4줄. 짧을수록 좋다.
- '교수님:' 같은 이름표, 따옴표, 설명을 붙이지 않는다.
- 모르는 사실(날짜, 장소, 금액)이 필요하면 그럴듯한 값으로 짧게 쓴다.
- 실제 학생 이름, 성적, 연락처 같은 개인정보는 만들지도 묻지도 않는다.
"""
    lines = ["# 교수님 카톡 실제 예시", "", "학생 메시지(S)와 교수님 답장(P). 이름은 OO로 가렸다.", ""]
    for room in ["group", "dm"]:
        for mood in ["ss", "nn", "ff"]:
            ex = [e for e in style["examples"] if e["room"] == room and e["mood"] == mood]
            if not ex:
                continue
            lines.append(f"## {mood} {MOOD_NAME[mood]} · {ROOM_NAME[room]} ({len(ex)}개)")
            lines.append("")
            for e in ex:
                lines.append(f"S: {e['s'] or '[교수님이 먼저 보냄]'}")
                for p in e["p"]:
                    lines.append(f"P: {p}")
                lines.append("")
    return instructions, "\n".join(lines)


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "web/gpt")
    style = json.loads((ROOT / "data" / "web_examples.json").read_text(encoding="utf-8"))
    instructions, examples = build(style)
    out.mkdir(parents=True, exist_ok=True)
    (out / "instructions.txt").write_text(instructions, encoding="utf-8")
    (out / "examples.md").write_text(examples, encoding="utf-8")
    print(f"{out}/instructions.txt ({len(instructions)}자), {out}/examples.md (예시 {len(style['examples'])}개)")


if __name__ == "__main__":
    main()

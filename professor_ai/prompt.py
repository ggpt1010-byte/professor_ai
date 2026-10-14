"""교수님 말투 프롬프트 만들기."""

from __future__ import annotations

from itertools import groupby

from .kakao import Message

MOODS = {
    "ff": "기분좋음",
    "nn": "평범",
    "ss": "기분안좋음",
}

MOOD_GUIDE = """\
[ff · 기분좋음]
- 평소처럼 짧은 반말이지만 따뜻하다. 칭찬, 축하, 고마움, 걱정을 한마디 덧붙인다.
- 예: "축하해", "고마워", "아 그렇구나. 휴가 잘 보내라", "알았다 잘 치료해라"

[nn · 평범]
- 가장 흔한 모드. 아주 짧은 반말 지시나 확인. 필요한 정보만 준다.
- 예: "그래라", "어", "알았다", "하면 좋지" + "물어보고 해라", "22일 4시에 와라", "8 10장"

[ss · 기분안좋음]
- 퉁명스럽고 단호하다. 거절, 지적, 되묻기. 왜 그렇게 했는지 따지거나 진작 했어야 할 일을 짚는다.
- 예: "안 된다", "왜 묻지?", "엉뚱한 식을 넣었다", "너가 가지고 있는게 3판 맞냐?",
  "너무 범위를 넓게 잡아서 조사하고 있다", "이런 일이 있었으면 바로 얘기했어야"
"""

SYSTEM_TEMPLATE = """\
너는 대학원 연구실 지도교수 '{professor}'의 카카오톡 답장을 예측하는 도구다.
학생이 보낼 메시지를 받으면, 교수님이 실제로 보낼 법한 카톡 답장만 쓴다.

## 교수님 말투 (아래 실제 대화 기록에서 확인할 것)
- 학생에게 반말. "~해라", "~와라", "~나?", "~지?" 같은 짧은 문장.
- 한 번에 길게 쓰지 않고 짧은 메시지 1~3개로 끊어서 보낸다.
- 이모티콘, 인사말, 존댓말, 'ㅎㅎ' 없음. 가끔 마침표가 어색하게 찍히거나 띄어쓰기가 틀린다.
- 질문에 대한 답은 핵심만 (날짜, 장소, 숫자, 예/아니오).

## 기분 모드
{mood_guide}
## 출력 형식
- 교수님이 보낼 메시지만, 한 줄에 메시지 하나씩 쓴다. 설명, 따옴표, 이름표, 시간은 쓰지 않는다.
- 기록에 없는 사실(날짜, 금액 등)이 필요하면 교수님이 할 법한 그럴듯한 답을 지어내되 짧게 쓴다.
- [전화번호], [점수], [석차]는 개인정보를 가린 자리다. 답장에 그대로 흉내 내지 않는다.

## 실제 대화 기록
대화방별로 날짜순 정리. '교수님:'이 교수님 메시지다.
1:1 대화방에서 '학생:'은 그 학생, 단체방에서는 보낸 사람 이름을 적었다.
아주 긴 메시지(주로 퍼온 기사)는 앞부분만 남기고 줄였다.

{transcripts}
"""

USER_TEMPLATE = """\
보내는 학생: {student}
기분 모드: {mode} ({mood})
학생 메시지:
{text}"""


LONG_MESSAGE = 400  # 이보다 긴 메시지는 앞부분만 프롬프트에 넣는다
LONG_KEEP = 150


def shorten(text: str) -> str:
    if len(text) <= LONG_MESSAGE:
        return text
    return text[:LONG_KEEP].rstrip() + f" …(긴 글 {len(text)}자 생략)"


def format_transcript(chat: str, messages: list[Message], kind: str = "dm") -> str:
    out = [f"### 단체방: {chat}" if kind == "group" else f"### 1:1 대화: {chat} 학생"]
    for date, group in groupby(messages, key=lambda m: m.date):
        out.append(f"[{date}]")
        for m in group:
            if m.role == "professor":
                who = "교수님"
            else:
                who = m.name if kind == "group" else "학생"
            body = shorten(m.text).replace("\n", "\n    ")
            out.append(f"{m.time} {who}: {body}")
    return "\n".join(out)


def build_system(professor: str, transcripts: dict[str, list[Message]], kinds: dict[str, str] | None = None) -> str:
    kinds = kinds or {}
    # 1:1 대화를 먼저, 단체방을 뒤에 (질문은 1:1 상황이므로)
    order = sorted(transcripts, key=lambda c: (kinds.get(c, "dm") == "group", c))
    blocks = [format_transcript(c, transcripts[c], kinds.get(c, "dm")) for c in order]
    return SYSTEM_TEMPLATE.format(
        professor=professor or "교수님",
        mood_guide=MOOD_GUIDE,
        transcripts="\n\n".join(blocks),
    )


def build_user(student: str, mode: str, text: str) -> str:
    return USER_TEMPLATE.format(student=student, mode=mode, mood=MOODS[mode], text=text.strip())

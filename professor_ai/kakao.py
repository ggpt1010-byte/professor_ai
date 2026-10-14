"""카카오톡 '대화 내보내기' .txt 파일 파서.

지원 형식 (PC 카카오톡):
    김철우 교수님 님과 카카오톡 대화
    저장한 날짜 : 2026-10-14 14:39:13

    --------------- 2023년 11월 27일 월요일 ---------------
    [김태현] [오후 7:12] 메시지 내용
    (여러 줄 메시지는 다음 줄로 이어짐)
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

DATE_RE = re.compile(r"^-+\s*(\d{4})년 (\d{1,2})월 (\d{1,2})일 \S+\s*-+$")
MSG_RE = re.compile(r"^\[(?P<name>[^\]]+)\] \[(?P<ampm>오전|오후) (?P<h>\d{1,2}):(?P<m>\d{2})\] ?(?P<text>.*)$")
TITLE_RE = re.compile(r"^(?P<name>.+?) 님과 카카오톡 대화$")
DELETED = "메시지가 삭제되었습니다."


@dataclass
class Message:
    date: str  # YYYY-MM-DD
    time: str  # HH:MM (24시간)
    name: str
    role: str  # "professor" | "student"
    text: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ParseResult:
    professor_name: str
    messages: list[Message]
    deleted_count: int


def _to_24h(ampm: str, h: str, m: str) -> str:
    hour = int(h) % 12
    if ampm == "오후":
        hour += 12
    return f"{hour:02d}:{m}"


def parse(text: str, professor_hint: str = "교수") -> ParseResult:
    """카톡 내보내기 텍스트를 메시지 목록으로 바꾼다.

    교수님은 파일 제목('OOO 님과 카카오톡 대화')의 상대방 이름으로 찾고,
    제목이 없으면 이름에 professor_hint가 들어간 사람으로 본다.
    """
    lines = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n").split("\n")

    professor_name = ""
    for line in lines[:5]:
        m = TITLE_RE.match(line.strip())
        if m:
            professor_name = m.group("name").strip()
            break

    messages: list[Message] = []
    deleted = 0
    date = None
    for raw in lines:
        line = raw.rstrip()
        dm = DATE_RE.match(line.strip())
        if dm:
            y, mo, d = dm.groups()
            date = f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
            continue
        if date is None:
            continue  # 파일 머리말
        if line.strip() == DELETED:
            deleted += 1
            continue
        mm = MSG_RE.match(line)
        if mm:
            name = mm.group("name").strip()
            if professor_name:
                role = "professor" if name == professor_name else "student"
            else:
                role = "professor" if professor_hint in name else "student"
            messages.append(
                Message(date, _to_24h(mm["ampm"], mm["h"], mm["m"]), name, role, mm["text"])
            )
        elif messages and messages[-1].date == date:
            messages[-1].text += "\n" + line  # 여러 줄 메시지의 이어지는 줄
    for msg in messages:
        msg.text = msg.text.strip("\n")

    if not professor_name:
        names = {m.name for m in messages if m.role == "professor"}
        professor_name = next(iter(names), "")
    return ParseResult(professor_name, messages, deleted)

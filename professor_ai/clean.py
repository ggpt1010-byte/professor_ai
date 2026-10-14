"""학습 전에 대화를 정리한다: 학습에 필요 없는 메시지 빼기 + 개인정보 가리기."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .kakao import Message

# 전화번호: 010-1234-5678, 02 3290 1357, 01012345678 ...
PHONE_RE = re.compile(r"(?<![\w/=?&.-])0\d{1,2}[-. ]?\d{3,4}[-. ]?\d{4}(?!\d)")
# 점수 목록 한 줄: '석예찬 (23) 3 3 3 7 5', '양재서 5 4 3 5 5 (22)', '성철현종 102 72 30'
SCORE_LINE_RE = re.compile(r"^\s*[가-힣]{2,5}\s*(\(\d+\))?(\s+\d+(\.\d+)?){1,}\s*(\(\d+\))?\s*$")
# 학생 석차: '38등에서 31등' (연구실 순위 '6등으로 선정' 같은 건 그대로 둔다)
RANK_RE = re.compile(r"\d+\s*등(\s*에서\s*)\d+\s*등")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
# 비밀번호가 언급된 메시지에서 숫자가 섞인 낱말은 비밀번호로 보고 가린다 ('kilby2002!', '킬비2002퍼센트다')
CRED_KW_RE = re.compile(r"(?i)(비밀번호|비번|패스워드|password|passwd|pwd|\bpw\b)")
SECRET_TOKEN_RE = re.compile(r"(?<![\w/])(?=\S*\d)(?=\S*[A-Za-z가-힣])[^\s:=]+")
# '2월6일까지', '3명' 처럼 숫자 뒤에 단위가 붙은 낱말은 비밀번호가 아니다
COUNT_WORD_RE = re.compile(r"\d+(년|월|일|시|분|초|명|개|번|차|주|장|층|호|원|점|등)")
# 키워드 없이 툭 던진 비밀번호 모양 낱말 ('kilby500%'): 영문+숫자+특수문자
BARE_SECRET_RE = re.compile(r"(?<![\w/@.])[A-Za-z]{2,}\d{2,}[%!@#$^&*]+(?![\w/])")
ID_RE = re.compile(r"(?i)\b(id|아이디)(\s*[:=]\s*)(\S+)")
URL_PWD_RE = re.compile(r"([?&]pwd=)[^&\s]+")
BARE_NAME_RE = re.compile(r"^[가-힣]{2,4}$")
# 통화 기록, 첨부만 있는 메시지 등 교수님 말투와 상관없는 시스템성 메시지
SYSTEM_RE = re.compile(r"^(보이스톡|페이스톡)( 해요| 부재중| 취소| \d+:\d+)?$")

PHONE_MASK = "[전화번호]"
EMAIL_MASK = "[이메일]"
SECRET_MASK = "[비밀번호]"
SCORE_MASK = "[점수]"
RANK_MASK = "[석차]"


@dataclass
class ExcludeRule:
    date: str
    start: str | None = None  # HH:MM, 없으면 하루 전체
    end: str | None = None
    note: str = ""

    def matches(self, msg: Message) -> bool:
        if msg.date != self.date:
            return False
        if self.start is None:
            return True
        return self.start <= msg.time <= (self.end or self.start)


@dataclass
class CleanReport:
    kept: int = 0
    removed: Counter = field(default_factory=Counter)
    masked: Counter = field(default_factory=Counter)

    def summary(self) -> str:
        parts = [f"학습에 쓴 메시지 {self.kept}개"]
        labels = {
            "score_memo": "점수 메모",
            "manual": "직접 지정한 제외 구간",
            "system": "보이스톡 등 시스템 메시지",
        }
        for key, n in self.removed.items():
            parts.append(f"{labels.get(key, key)} {n}개 제외")
        for key, n in self.masked.items():
            parts.append(f"{key} {n}곳 가림")
        return ", ".join(parts)


def load_exclude_rules(path: Path) -> list[ExcludeRule]:
    """exclude.txt 형식: 한 줄에 하나, '#' 뒤는 메모.

        2025-07-09                  # 그날 전체
        2025-09-05 15:31-16:19      # 그 시간 구간
    """
    rules: list[ExcludeRule] = []
    if not path.exists():
        return rules
    for raw in path.read_text(encoding="utf-8").splitlines():
        body, _, note = raw.partition("#")
        body = body.strip()
        if not body:
            continue
        date, _, span = body.partition(" ")
        span = span.strip()
        if span:
            start, _, end = span.partition("-")
            rules.append(ExcludeRule(date, start.strip(), (end or start).strip(), note.strip()))
        else:
            rules.append(ExcludeRule(date, note=note.strip()))
    return rules


def is_score_memo(msg: Message) -> bool:
    """학생이 남긴 점수 목록 메모인지 (줄의 절반 이상이 '이름 숫자 숫자...' 형태)."""
    if msg.role != "student":
        return False
    lines = [ln for ln in msg.text.splitlines() if ln.strip()]
    if not lines:
        return False
    hits = sum(bool(SCORE_LINE_RE.match(ln)) for ln in lines)
    return hits >= 1 and hits * 2 >= len(lines)


def mask_text(text: str, report: CleanReport | None = None) -> str:
    def count(kind: str, n: int) -> None:
        if report is not None and n:
            report.masked[kind] += n

    text, n = PHONE_RE.subn(PHONE_MASK, text)
    count("전화번호", n)
    out_lines = []
    for ln in text.splitlines():
        if SCORE_LINE_RE.match(ln):
            name = ln.split()[0]
            out_lines.append(f"{name} {SCORE_MASK}")
            count("점수", 1)
        else:
            out_lines.append(ln)
    text = "\n".join(out_lines)
    text, n = RANK_RE.subn(lambda m: f"{RANK_MASK}{m.group(1)}{RANK_MASK}", text)
    count("석차", n * 2)
    text, n = EMAIL_RE.subn(EMAIL_MASK, text)
    count("이메일", n)
    text, n = URL_PWD_RE.subn(lambda m: m.group(1) + SECRET_MASK, text)
    count("비밀번호", n)
    text, n = BARE_SECRET_RE.subn(SECRET_MASK, text)
    count("비밀번호", n)
    if CRED_KW_RE.search(text):
        text, n = ID_RE.subn(lambda m: m.group(1) + m.group(2) + "[아이디]", text)
        count("아이디", n)
        masked_lines = []
        for ln in text.splitlines():
            if "http" in ln:
                masked_lines.append(ln)
                continue
            hits = [t for t in SECRET_TOKEN_RE.findall(ln) if not COUNT_WORD_RE.search(t)]
            ln = SECRET_TOKEN_RE.sub(
                lambda m: m.group(0) if COUNT_WORD_RE.search(m.group(0)) else SECRET_MASK, ln
            )
            count("비밀번호", len(hits))
            masked_lines.append(ln)
        text = "\n".join(masked_lines)
    return text


def clean(messages: list[Message], rules: list[ExcludeRule]) -> tuple[list[Message], CleanReport]:
    report = CleanReport()

    # 교수님이 한마디도 안 한 날, 학생이 이름만 덩그러니 보낸 메시지도 메모로 본다 (예: '이우진')
    professor_days = {m.date for m in messages if m.role == "professor"}

    kept: list[Message] = []
    for msg in messages:
        if any(r.matches(msg) for r in rules):
            report.removed["manual"] += 1
            continue
        if SYSTEM_RE.match(msg.text.strip()):
            report.removed["system"] += 1
            continue
        if is_score_memo(msg) or (
            msg.role == "student"
            and msg.date not in professor_days
            and BARE_NAME_RE.match(msg.text.strip())
        ):
            report.removed["score_memo"] += 1
            continue
        kept.append(Message(msg.date, msg.time, msg.name, msg.role, mask_text(msg.text, report)))
    report.kept = len(kept)
    return kept, report

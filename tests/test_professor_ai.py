from pathlib import Path

import pytest

from professor_ai import cli, store
from professor_ai.clean import clean, load_exclude_rules, mask_text
from professor_ai.kakao import parse

SAMPLE = """﻿김철우 교수님 님과 카카오톡 대화\r
저장한 날짜 : 2026-10-14 14:39:13\r
\r
--------------- 2025년 1월 2일 목요일 ---------------\r
[김태현] [오후 4:27] 교수님 질문 있습니다.\r
두 번째 줄입니다.\r
[김철우 교수님] [오후 4:29] 그래라\r
메시지가 삭제되었습니다.\r
[김철우 교수님] [오전 12:50] 왜 묻지?\r
--------------- 2025년 7월 9일 수요일 ---------------\r
[김태현] [오후 1:04] 02 3290 1357 입니다\r
--------------- 2025년 12월 20일 토요일 ---------------\r
[김태현] [오후 1:15] 김태현 16 13 9 15 12\r
--------------- 2025년 12월 30일 화요일 ---------------\r
[김태현] [오후 6:04] 이우진\r
--------------- 2026년 6월 9일 화요일 ---------------\r
[김철우 교수님] [오후 4:27] 보이스톡 0:10\r
[김철우 교수님] [오후 4:27] 혹시 핸드폰 봤나 010-4742-5648\r
"""


def test_parse():
    r = parse(SAMPLE)
    assert r.professor_name == "김철우 교수님"
    assert r.deleted_count == 1
    first = r.messages[0]
    assert (first.date, first.time, first.role) == ("2025-01-02", "16:27", "student")
    assert first.text == "교수님 질문 있습니다.\n두 번째 줄입니다."
    assert r.messages[2].time == "00:50"
    assert r.messages[1].role == "professor"


def test_clean(tmp_path: Path):
    rules_file = tmp_path / "exclude.txt"
    rules_file.write_text("2025-07-09  # 잘못 보낸 번호\n", encoding="utf-8")
    kept, report = clean(parse(SAMPLE).messages, load_exclude_rules(rules_file))
    texts = [m.text for m in kept]
    assert "이우진" not in texts  # 교수님 답 없는 날의 이름 메모
    assert not any("16 13 9" in t for t in texts)  # 점수 메모
    assert not any("3290" in t for t in texts)  # 수동 제외
    assert not any(t.startswith("보이스톡") for t in texts)
    assert "혹시 핸드폰 봤나 [전화번호]" in texts
    assert report.removed["score_memo"] == 2


def test_mask_scores_and_rank():
    assert mask_text("최민영 (48) 10 7 7 14 10") == "최민영 [점수]"
    assert mask_text("38등에서 31등 정도") == "[석차]에서 [석차] 정도"
    assert mask_text("우리는 6등으로 선정되었다") == "우리는 6등으로 선정되었다"
    assert mask_text("34만 6천원, 2025_2R, 공학관 448호") == "34만 6천원, 2025_2R, 공학관 448호"


def test_question_mode_never_writes(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(store, "ROOT", tmp_path)
    src = tmp_path / "김태현_카톡.txt"
    src.write_text(SAMPLE, encoding="utf-8")
    cli.learn(src)
    assert store.list_students() == ["김태현"]
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    out = cli.ask("김태현", "ss", "교수님 이건 저장되면 안 됩니다", dry_run=True)
    assert "기분안좋음" in out

    after = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after
    assert all("저장되면 안 됩니다" not in m.text for m in store.load_messages("김태현"))


def test_relearn_dedupes(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(store, "ROOT", tmp_path)
    src = tmp_path / "김태현_카톡.txt"
    src.write_text(SAMPLE, encoding="utf-8")
    cli.learn(src)
    n = len(store.load_messages("김태현"))
    cli.learn(src)
    assert len(store.load_messages("김태현")) == n


@pytest.mark.parametrize("line,expected", [("ff 안녕", "ff"), ("SS 왜", "ss"), ("nn\n두 줄", "nn")])
def test_question_prefix(line, expected):
    assert cli.QUESTION_RE.match(line).group(1).lower() == expected


def test_not_a_question():
    assert cli.QUESTION_RE.match("ffff 안녕") is None
    assert cli.QUESTION_RE.match("교수님 ff") is None


@pytest.mark.parametrize(
    "text,expected",
    [
        ("id: abc\npwd: secret2002!\n입니다", "id: [아이디]\npwd: [비밀번호]\n입니다"),
        ("비번은 비밀2002퍼센트다", "비번은 [비밀번호]"),
        ("email: me@korea.ac.kr password: abc123", "email: [이메일] password: [비밀번호]"),
        ("JSSC와 TVLSI 비번 abc2026", "JSSC와 TVLSI 비번 [비밀번호]"),
        ("연구재단 id 비번이 뭐지?", "연구재단 id 비번이 뭐지?"),
        ("내년2월6일까지 쓰고 패스워드 아는 사람?", "내년2월6일까지 쓰고 패스워드 아는 사람?"),
        ("https://x.zoom.us/j/123?pwd=AbC1.2", "https://x.zoom.us/j/123?pwd=[비밀번호]"),
    ],
)
def test_mask_credentials(text, expected):
    assert mask_text(text) == expected


GROUP = """AISL 학생 님과 카카오톡 대화
저장한 날짜 : 2026-10-14 14:47:17

--------------- 2025년 4월 7일 월요일 ---------------
전진우님이 신제우님, 김태현님을 초대했습니다.
--------------- 2025년 4월 10일 목요일 ---------------
[김철우 교수님] [오전 10:59] 새로 방을 만들었다
팀 이름이 변경되었습니다.
[성철이형] [오후 2:19] 네 알겠습니다
두 번째 줄
[김태현] [오후 2:20] 확인했습니다
박진우님이 나갔습니다.
"""


def test_group_chat(tmp_path: Path, monkeypatch):
    r = parse(GROUP)
    assert r.is_group
    assert r.professor_name == "김철우 교수님"
    assert [m.role for m in r.messages] == ["professor", "student", "student"]
    assert r.messages[0].text == "새로 방을 만들었다"
    assert r.messages[1].text == "네 알겠습니다\n두 번째 줄"
    assert r.messages[2].text == "확인했습니다"

    monkeypatch.setattr(store, "ROOT", tmp_path)
    src = tmp_path / "AISL_전체톡방_카톡.txt"
    src.write_text(GROUP, encoding="utf-8")
    cli.learn(src)
    assert store.list_chats() == ["AISL_전체톡방"]
    assert store.list_students() == []
    out = cli.ask("김태현", "nn", "질문", dry_run=True)
    assert "### 단체방: AISL_전체톡방" in out and "성철이형: 네 알겠습니다" in out

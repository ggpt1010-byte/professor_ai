"""명령줄 / 대화형 화면.

학습 모드  : 카톡 .txt 파일을 주면 학습 (data/ 에 저장)
질문 모드  : ff / nn / ss 로 시작하는 메시지는 질문 (어디에도 저장하지 않음)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from . import store
from .clean import clean, load_exclude_rules
from .kakao import parse
from .prompt import MOODS, build_system, build_user

QUESTION_RE = re.compile(r"^(ff|nn|ss)\s+(.+)$", re.S | re.I)


def guess_student(path: Path) -> str:
    """'김태현_카톡.txt' -> '김태현'"""
    return re.split(r"[_\s.-]", path.stem, maxsplit=1)[0]


def learn(path: Path, student: str | None = None) -> str:
    student = student or guess_student(path)
    text = path.read_text(encoding="utf-8-sig")
    parsed = parse(text)
    if not parsed.messages:
        raise ValueError(f"{path.name}에서 카톡 메시지를 찾지 못했습니다. 카카오톡 '대화 내보내기' 파일이 맞나요?")
    rules = load_exclude_rules(store.exclude_path(student))
    kept, report = clean(parsed.messages, rules)
    added, total = store.save_learned(student, kept, parsed.professor_name, path.name)
    lines = [
        f"[학습 완료] 학생: {student} / 교수님: {parsed.professor_name or '(이름 못 찾음)'}",
        f"  {report.summary()}, 삭제된 메시지 {parsed.deleted_count}개 제외",
        f"  새로 추가 {added}개, 지금까지 학습한 메시지 {total}개",
    ]
    return "\n".join(lines)


def pick_student(student: str | None) -> str:
    students = store.list_students()
    if student:
        if student not in students:
            raise SystemExit(f"'{student}' 학생의 학습 기록이 없습니다. 학습된 학생: {', '.join(students) or '없음'}")
        return student
    if len(students) == 1:
        return students[0]
    if not students:
        raise SystemExit("학습된 대화가 없습니다. 먼저 카톡 .txt 파일로 학습시켜 주세요.")
    raise SystemExit(f"학생을 골라 주세요 (--student). 학습된 학생: {', '.join(students)}")


def ask(student: str, mode: str, text: str, *, dry_run: bool = False, model: str | None = None) -> str:
    mode = mode.lower()
    if mode not in MOODS:
        raise SystemExit("모드는 ff(기분좋음), nn(평범), ss(기분안좋음) 중 하나입니다.")
    if dry_run:
        from .predict import load_context

        professor, transcripts = load_context()
        return build_system(professor, transcripts) + "\n\n===== 질문 =====\n" + build_user(student, mode, text)
    from .predict import PredictError, predict

    try:
        return predict(student, mode, text, model=model)
    except PredictError as e:
        return f"[오류] {e}"


def repl(student: str | None, model: str | None) -> int:
    print("교수님 AI")
    print("  질문: ff / nn / ss 로 시작 (예: ff 교수님 내일 줌으로 참석해도 될까요?)  ← 저장 안 됨")
    print("  학습: 카톡 .txt 파일 경로를 입력하거나 끌어다 놓기")
    print("  /학생 이름 : 질문하는 학생 바꾸기,  q : 끝내기")
    current = student
    while True:
        try:
            line = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            continue
        if line.lower() in {"q", "quit", "exit", "종료"}:
            return 0
        if line.startswith("/학생"):
            current = line.removeprefix("/학생").strip() or None
            print(f"질문하는 학생: {current or '(자동)'}")
            continue
        m = QUESTION_RE.match(line)
        if m:
            try:
                who = pick_student(current)
            except SystemExit as e:
                print(e)
                continue
            print(f"\n[{m.group(1).lower()} · {MOODS[m.group(1).lower()]}] 교수님 예상 답장")
            print(ask(who, m.group(1), m.group(2), model=model))
            continue
        path = Path(line.strip("'\""))
        if path.suffix.lower() == ".txt" and path.exists():
            try:
                print(learn(path))
            except (ValueError, UnicodeDecodeError) as e:
                print(f"[오류] {e}")
            continue
        print("질문은 ff / nn / ss 로 시작해 주세요. 학습은 카톡 .txt 파일 경로를 입력해 주세요. (아무것도 저장하지 않았습니다)")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="python -m professor_ai", description="교수님 예상 카톡 답장")
    p.add_argument("--model", help="Claude 모델 (기본: PROFESSOR_AI_MODEL 또는 claude-opus-5-5)")
    sub = p.add_subparsers(dest="cmd")

    pl = sub.add_parser("learn", help="카톡 .txt 파일로 학습")
    pl.add_argument("file", type=Path)
    pl.add_argument("--student", help="학생 이름 (기본: 파일 이름 앞부분)")

    pa = sub.add_parser("ask", help="예상 답장 받기 (저장 안 됨)")
    pa.add_argument("mode", choices=sorted(MOODS), type=str.lower)
    pa.add_argument("text", nargs="+")
    pa.add_argument("--student")
    pa.add_argument("--dry-run", action="store_true", help="API를 부르지 않고 보낼 프롬프트만 출력")

    sub.add_parser("students", help="학습된 학생 목록")

    args = p.parse_args(argv)
    if args.cmd == "learn":
        print(learn(args.file, args.student))
    elif args.cmd == "ask":
        print(ask(pick_student(args.student), args.mode, " ".join(args.text), dry_run=args.dry_run, model=args.model))
    elif args.cmd == "students":
        for s in store.list_students():
            meta = store.load_meta(s)
            print(f"{s}: 메시지 {meta.get('message_count', '?')}개, 마지막 학습 {meta.get('last_learned_at', '?')}")
    else:
        return repl(None, args.model)
    return 0

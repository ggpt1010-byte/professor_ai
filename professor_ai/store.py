"""학생별 학습 데이터 저장소 (data/students/<학생 이름>/).

학습 모드에서만 쓰기가 일어난다. 질문 모드는 이 모듈의 읽기 함수만 쓴다.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from .kakao import Message

ROOT = Path(os.environ.get("PROFESSOR_AI_DATA", Path(__file__).resolve().parent.parent / "data"))


def students_dir() -> Path:
    return ROOT / "students"


def student_dir(student: str) -> Path:
    return students_dir() / student


def exclude_path(student: str) -> Path:
    return student_dir(student) / "exclude.txt"


def list_students() -> list[str]:
    d = students_dir()
    if not d.exists():
        return []
    return sorted(p.name for p in d.iterdir() if (p / "messages.jsonl").exists())


def load_messages(student: str) -> list[Message]:
    path = student_dir(student) / "messages.jsonl"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [Message(**json.loads(line)) for line in f if line.strip()]


def load_meta(student: str) -> dict:
    path = student_dir(student) / "meta.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_learned(student: str, new: list[Message], professor_name: str, source: str) -> tuple[int, int]:
    """기존 기록과 합쳐 저장한다. 같은 메시지는 한 번만 남긴다. (추가된 수, 전체 수)를 돌려준다."""
    d = student_dir(student)
    d.mkdir(parents=True, exist_ok=True)
    old = load_messages(student)
    seen = {(m.date, m.time, m.role, m.text) for m in old}
    added = [m for m in new if (m.date, m.time, m.role, m.text) not in seen]
    merged = sorted(old + added, key=lambda m: (m.date, m.time))
    # 정렬은 안정적이라 같은 분에 보낸 메시지의 순서는 유지된다.

    with (d / "messages.jsonl").open("w", encoding="utf-8") as f:
        for m in merged:
            f.write(json.dumps(m.to_dict(), ensure_ascii=False) + "\n")

    meta = load_meta(student)
    meta.update(
        {
            "student": student,
            "professor_name": professor_name,
            "message_count": len(merged),
            "last_learned_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    meta.setdefault("sources", [])
    if source not in meta["sources"]:
        meta["sources"].append(source)
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(added), len(merged)
